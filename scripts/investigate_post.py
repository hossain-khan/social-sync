#!/usr/bin/env python
"""
Investigation script for specific post sync
"""
import json
import sys

from atproto import Client

# The post we're investigating
POST_RKEY = "3m5x5kzlnoc2u"
POST_URI = f"at://did:plc:sek23f2vucrxxyaaud2emnxe/app.bsky.feed.post/{POST_RKEY}"


def investigate_post():
    """Investigate the specific post"""
    print(f"Investigating post: {POST_URI}")
    print(f"Bluesky URL: https://bsky.app/profile/hossain.dev/post/{POST_RKEY}")
    print(f"Mastodon URL: https://androiddev.social/@hossainkhan/115574844282948368")
    print("\n" + "=" * 80 + "\n")

    # Try to get post details from AT Protocol
    client = Client()

    try:
        # Parse the URI
        did = "did:plc:sek23f2vucrxxyaaud2emnxe"
        collection = "app.bsky.feed.post"

        # Get the post record
        print("Fetching post from AT Protocol...")
        response = client.com.atproto.repo.get_record(
            {"repo": did, "collection": collection, "rkey": POST_RKEY}
        )

        print("\n📝 POST RECORD:")
        print(response)

        # Extract key fields
        record = response.value if hasattr(response, "value") else response

        print("\n" + "=" * 80)
        print("\n🔍 KEY INFORMATION:")
        print(f"  Text: {getattr(record, 'text', 'N/A')}")
        print(f"  Created: {getattr(record, 'created_at', 'N/A')}")
        print(f"  Languages: {getattr(record, 'langs', 'N/A')}")
        print(f"  Is Reply: {hasattr(record, 'reply') and record.reply is not None}")
        print(f"  Has Embed: {hasattr(record, 'embed') and record.embed is not None}")
        print(
            f"  Has Facets: {hasattr(record, 'facets') and record.facets is not None}"
        )
        print(f"  Self Labels: {getattr(record, 'labels', 'N/A')}")

        # Check for reply information
        if hasattr(record, "reply") and record.reply is not None:
            print("\n🧵 REPLY INFORMATION:")
            reply = record.reply
            print(
                f"  Parent: {getattr(reply.parent, 'uri', 'N/A') if hasattr(reply, 'parent') else 'N/A'}"
            )
            print(
                f"  Root: {getattr(reply.root, 'uri', 'N/A') if hasattr(reply, 'root') else 'N/A'}"
            )

        # Check for embed information
        if hasattr(record, "embed") and record.embed is not None:
            print("\n📎 EMBED INFORMATION:")
            embed = record.embed
            print(f"  Type: {getattr(embed, 'py_type', 'N/A')}")
            if hasattr(embed, "external"):
                ext = embed.external
                print(f"  External URL: {getattr(ext, 'uri', 'N/A')}")
                print(f"  Title: {getattr(ext, 'title', 'N/A')}")
                print(f"  Description: {getattr(ext, 'description', 'N/A')}")
            if hasattr(embed, "images"):
                print(f"  Images: {len(embed.images)} image(s)")
            if hasattr(embed, "record"):
                print(f"  Quoted Post: {getattr(embed.record, 'uri', 'N/A')}")

        # Check for facets (links, mentions, hashtags)
        if hasattr(record, "facets") and record.facets:
            print("\n🔗 FACETS (Rich Text):")
            for i, facet in enumerate(record.facets):
                features = getattr(facet, "features", [])
                for feature in features:
                    ftype = getattr(feature, "py_type", "unknown")
                    print(f"  [{i}] Type: {ftype}")
                    if hasattr(feature, "uri"):
                        print(f"      URI: {feature.uri}")
                    if hasattr(feature, "did"):
                        print(f"      DID: {feature.did}")
                    if hasattr(feature, "tag"):
                        print(f"      Tag: {feature.tag}")

        # Check for facets (links, mentions, hashtags)
        if "facets" in record:
            print("\n🔗 FACETS (Rich Text):")
            for i, facet in enumerate(record["facets"]):
                features = facet.get("features", [])
                for feature in features:
                    ftype = feature.get("$type", "unknown")
                    print(f"  [{i}] Type: {ftype}")
                    if "uri" in feature:
                        print(f"      URI: {feature['uri']}")
                    if "did" in feature:
                        print(f"      DID: {feature['did']}")
                    if "tag" in feature:
                        print(f"      Tag: {feature['tag']}")

        print("\n" + "=" * 80)
        print("\n✅ WHY WAS THIS POST SYNCED?")

        # Check sync eligibility
        is_reply = hasattr(record, "reply") and record.reply is not None
        text = getattr(record, "text", "")
        has_no_sync_tag = "#no-sync" in text.lower()

        # Check if this is a QUOTE POST
        is_quote_post = False
        quoted_author_did = None
        if hasattr(record, "embed") and record.embed is not None:
            embed = record.embed
            if hasattr(embed, "py_type") and embed.py_type == "app.bsky.embed.record":
                is_quote_post = True
                if hasattr(embed, "record") and hasattr(embed.record, "uri"):
                    quoted_uri = embed.record.uri
                    quoted_author_did = (
                        quoted_uri.split("/")[2] if "/" in quoted_uri else None
                    )
                    print(f"  🔍 QUOTE POST DETECTED!")
                    print(f"     Quoted post URI: {quoted_uri}")
                    print(f"     Quoted author DID: {quoted_author_did}")
                    print(f"     Your DID: {did}")

                    if quoted_author_did == did:
                        print(f"     → This is a SELF-QUOTE (quoting own post)")
                    else:
                        print(f"     → This is quoting SOMEONE ELSE's post")

        if is_reply:
            reply = record.reply
            root_uri = getattr(reply.root, "uri", "") if hasattr(reply, "root") else ""
            root_did = root_uri.split("/")[2] if "/" in root_uri else ""
            is_self_thread = root_did == did

            if is_self_thread:
                print("  ✓ This is a SELF-REPLY (reply to own thread)")
                print("    → Self-replies ARE synced to maintain thread continuity")
            else:
                print("  ✗ This is a reply to someone else's thread")
                print("    → Should have been FILTERED OUT")
        elif is_quote_post:
            if quoted_author_did and quoted_author_did != did:
                print("  ❌ THIS IS A QUOTE POST OF SOMEONE ELSE'S CONTENT")
                print("     → Should have been FILTERED OUT!")
                print("     → This is a BUG - quote posts should not be synced")
            else:
                print("  ⚠️  This is a self-quote (quoting own post)")
                print("     → May or may not want to sync these")
        else:
            print("  ✓ This is a ROOT POST (not a reply)")
            print("    → Root posts ARE synced")

        if has_no_sync_tag:
            print("  ✗ Contains #no-sync tag")
            print("    → Should have been SKIPPED")
        else:
            print("  ✓ No #no-sync tag present")
            print("    → Post eligible for sync")

        # Check if already synced
        with open("sync_state.json", "r") as f:
            state = json.load(f)

        synced_entry = None
        for entry in state.get("synced_posts", []):
            if entry["bluesky_uri"] == POST_URI:
                synced_entry = entry
                break

        if synced_entry:
            print(f"\n  ✓ CONFIRMED: Post was synced on {synced_entry['synced_at']}")
            print(f"    → Mastodon ID: {synced_entry['mastodon_id']}")
        else:
            print("\n  ✗ NOT FOUND in sync state")

    except Exception as e:
        print(f"\n❌ Error fetching post: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    investigate_post()
