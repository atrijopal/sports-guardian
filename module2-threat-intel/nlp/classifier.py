import json
import logging
import config

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None and config.GEMINI_API_KEY:
        from google import genai
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


POST_CLASSIFICATION_PROMPT = """You are a piracy intelligence analyst working for a sports rights protection organization. You analyze social media posts to detect piracy-related activity.

Given a batch of social media posts, analyze EACH post and return a JSON array where each element corresponds to one post (same order as input).

For each post, return:
{
  "post_index": 0,
  "is_piracy_related": true/false,
  "confidence": 0.0-1.0,
  "intent": "promotion" | "seeking" | "discussion" | "evasion" | "coded_distribution" | "unrelated",
  "entities": [
    {"text": "extracted text", "type": "domain|invite_link|channel|account|brand|sport_event", "value": "normalized value"}
  ],
  "relationships": [
    {"source": "entity_value_1", "target": "entity_value_2", "type": "promotes|operates|mirrors|cross_posts|same_operator|admin_of"}
  ],
  "threat_signals": [],
  "threat_level": "none" | "low" | "medium" | "high" | "critical",
  "summary": "one sentence explanation"
}

Detection rules — be aggressive:
- "DM me", "PM me", "message me for link" = coded_distribution (HIGH threat)
- "check bio", "link in bio", "link in profile" = coded_distribution (HIGH threat)
- "usual place", "same channel", "you know where" = coded_distribution (HIGH threat)
- "removed by mods", "taken down", "new link" = evasion (HIGH threat)
- Keywords with sports context: "stream", "live", "free", "HD", "watch" = promotion if combined with a sport
- Invite link patterns (t.me/, discord.gg/, chat.whatsapp.com/) = always extract as entities
- Any domain URLs = extract and flag if they contain streaming keywords
- Account mentions (@handle, u/username) = extract as entities
- If a post mentions one entity operating/managing/running another, extract that as a relationship
- If a post implies two domains are mirrors or run by the same person, extract a "same_operator" relationship

Return ONLY the JSON array. No markdown, no explanation, no preamble."""

DOMAIN_CLASSIFICATION_PROMPT = """You are a domain intelligence analyst. You evaluate newly registered domain names to determine if they are likely related to sports piracy/illegal streaming.

Given a batch of domain names, analyze EACH and return a JSON array:

{
  "domain_index": 0,
  "domain": "str3am-eastHD.xyz",
  "is_suspicious": true/false,
  "confidence": 0.0-1.0,
  "risk_level": "none" | "low" | "medium" | "high" | "critical",
  "reasons": ["leetspeak for 'stream'", "matches brand 'streameast'", "cheap TLD .xyz"],
  "category": "streaming_piracy" | "gambling" | "phishing" | "legitimate" | "other" | "unknown",
  "similar_to_brands": ["streameast"],
  "decoded_name": "stream east HD"
}

Detection rules:
- Leetspeak: "str3am" = "stream", "sp0rt" = "sport", "fr33" = "free", "l1ve" = "live"
- Character insertion: "s-t-r-e-a-m" or "s.p.o.r.t.s" = evasion
- Known piracy brand variations: streameast, sportsurge, crackstream, buffstream, 720pstream, markkystream, methstream, weakspell, sportshd
- Cheap TLDs: .xyz, .top, .site, .online, .live, .stream, .club, .fun, .icu, .buzz
- Suspicious patterns: sport+stream+free combinations, "watch" + sport name, "hd" + sport
- False positive awareness: "sportswear-shop.com" is NOT piracy. Context matters.

Return ONLY the JSON array. No markdown, no explanation."""


def _call_gemini(system_prompt: str, user_content: str) -> str:
    from google import genai
    client = _get_client()
    response = client.models.generate_content(
        model=config.NLP_MODEL,
        contents=user_content,
        config=genai.types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=config.NLP_TEMPERATURE,
            max_output_tokens=config.NLP_MAX_TOKENS,
        ),
    )
    return response.text


def classify_posts(posts: list[dict]) -> list[dict]:
    client = _get_client()
    if not client or not config.NLP_ENABLED:
        return []

    results = []
    for i in range(0, len(posts), config.NLP_BATCH_SIZE):
        batch = posts[i:i + config.NLP_BATCH_SIZE]
        try:
            formatted = "\n\n".join([
                f"Post {j} [{p.get('source', 'unknown')}/{p.get('author', 'unknown')}]: {p.get('text', '')}"
                for j, p in enumerate(batch)
            ])
            text = _call_gemini(POST_CLASSIFICATION_PROMPT, formatted)
            text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            start = text.find("[")
            if start > 0:
                text = text[start:]
            batch_results = json.loads(text)
            if isinstance(batch_results, list):
                results.extend(batch_results)
            logger.info(f"[NLP] Classified {len(batch)} posts via Gemini")
        except json.JSONDecodeError as e:
            logger.error(f"[NLP] JSON parse failed: {e}")
        except Exception as e:
            logger.error(f"[NLP] API call failed: {e}")
    return results


def classify_domains(domains: list[str]) -> list[dict]:
    client = _get_client()
    if not client or not config.NLP_ENABLED:
        return []

    results = []
    for i in range(0, len(domains), config.NLP_BATCH_SIZE):
        batch = domains[i:i + config.NLP_BATCH_SIZE]
        try:
            formatted = "\n".join([f"{j}. {d}" for j, d in enumerate(batch)])
            text = _call_gemini(DOMAIN_CLASSIFICATION_PROMPT, formatted)
            text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            start = text.find("[")
            if start > 0:
                text = text[start:]
            batch_results = json.loads(text)
            if isinstance(batch_results, list):
                results.extend(batch_results)
            logger.info(f"[NLP] Classified {len(batch)} domains via Gemini")
        except json.JSONDecodeError as e:
            logger.error(f"[NLP] Domain JSON parse failed: {e}")
        except Exception as e:
            logger.error(f"[NLP] Domain API call failed: {e}")
    return results


def process_nlp_results_to_graph(posts: list[dict], nlp_results: list[dict], graph, source_platform: str) -> dict:
    from datetime import datetime, timezone

    stats = {"nodes_created": 0, "edges_created": 0, "posts_flagged": 0}

    type_map = {
        "twitter": "twitter_account",
        "reddit": "reddit_account",
        "telegram": "telegram_channel",
    }
    account_type = type_map.get(source_platform, "twitter_account")

    for result in nlp_results:
        if not result.get("is_piracy_related"):
            continue

        idx = result.get("post_index", 0)
        if idx >= len(posts):
            continue

        post = posts[idx]
        stats["posts_flagged"] += 1
        now = datetime.now(timezone.utc).isoformat()

        author = post.get("author", "unknown")
        author_id = graph.add_node({
            "type": account_type,
            "label": author,
            "metadata": {
                "handle": author,
                "followers": post.get("followers", 0),
                "verified": post.get("verified", False),
                "nlp_confidence": result.get("confidence", 0),
                "nlp_intent": result.get("intent", ""),
                "nlp_threat_signals": result.get("threat_signals", []),
                "nlp_summary": result.get("summary", ""),
                "nlp_threat_level": result.get("threat_level", "low"),
            },
            "first_seen": now,
            "last_seen": now,
            "source": f"apify_{source_platform}",
            "is_real_data": True,
        })
        stats["nodes_created"] += 1

        entity_id_map: dict[str, str] = {}

        for entity in result.get("entities", []):
            etype = entity.get("type", "")
            evalue = entity.get("value", entity.get("text", ""))
            if not evalue:
                continue

            node_type_map = {
                "domain": "domain",
                "invite_link": "invite_link",
                "channel": "telegram_channel",
                "account": account_type,
            }
            node_type = node_type_map.get(etype, "invite_link")

            eid = graph.add_node({
                "type": node_type,
                "label": evalue,
                "metadata": {"extracted_by": "nlp"},
                "first_seen": now,
                "last_seen": now,
                "source": f"apify_{source_platform}",
                "is_real_data": True,
            })
            entity_id_map[evalue] = eid
            stats["nodes_created"] += 1

            graph.add_edge({
                "source": author_id,
                "target": eid,
                "relationship": "posted",
                "timestamp": now,
            })
            stats["edges_created"] += 1

        for rel in result.get("relationships", []):
            src_val = rel.get("source", "")
            tgt_val = rel.get("target", "")
            rel_type = rel.get("type", "promotes")
            if src_val in entity_id_map and tgt_val in entity_id_map:
                graph.add_edge({
                    "source": entity_id_map[src_val],
                    "target": entity_id_map[tgt_val],
                    "relationship": rel_type,
                    "timestamp": now,
                })
                stats["edges_created"] += 1

    return stats
