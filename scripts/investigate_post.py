#!/usr/bin/env python
"""
Investigation script for Bluesky post sync analysis

This utility helps investigate why a specific Bluesky post was or wasn't synced
to Mastodon by fetching and analyzing the post's AT Protocol data.

Usage:
    python scripts/investigate_post.py <post_rkey> [did]

    # Using post URL: https://bsky.app/profile/user.bsky.social/post/3m5x5kzlnoc2u
    python scripts/investigate_post.py 3m5x5kzlnoc2u

    # Or specify custom DID:
    python scripts/investigate_post.py 3m5x5kzlnoc2u did:plc:custom123
"""
import argparse
import json
import sys

from atproto import Client


def investigate_post(post_rkey: str, user_did: str = None):
    """Investigate a specific Bluesky post

    Args:
        post_rkey: Post record key (from Bluesky URL)
        user_did: Optional DID to use as post author (defaults to loading from sync_state.json)
    """
    # Load user DID from sync state if not provided
    if not user_did:
        try:
            with open("sync_state.json", "r") as f:
                state = json.load(f)
            if state.get("synced_posts"):
                # Extract DID from any synced post URI
                sample_uri = state["synced_posts"][0]["bluesky_uri"]
                user_did = sample_uri.split("/")[2] if "/" in sample_uri else None
        except (FileNotFoundError, KeyError, IndexError):
            pass

    if not user_did:
        print("❌ Error: Could not determine user DID.")
        print("   Either provide it as argument or ensure sync_state.json exists.")
        return False

    post_uri = f"at://{user_did}/app.bsky.feed.post/{post_rkey}"

    print(f"🔍 Investigating Post")
    print(f"   AT URI: {post_uri}")
    print(f"   Record Key: {post_rkey}")
    print(f"   User DID: {user_did}")
    print("\n" + "=" * 80 + "\n")

    # Try to get post details from AT Protocol
    client = Client()

    try:
        collection = "app.bsky.feed.post"

        # Get the post record
        print("📡 Fetching post from AT Protocol...")
        response = client.com.atproto.repo.get_record(
            {"repo": user_did, "collection": collection, "rkey": post_rkey}
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

        print("\n" + "=" * 80)
        print("\n🔍 SYNC ELIGIBILITY ANALYSIS")

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
                    print(f"\n📌 Quote Post Detection:")
                    print(f"   Quoted URI: {quoted_uri}")
                    print(f"   Quoted author: {quoted_author_did}")
                    print(f"   Post author: {user_did}")

                    if quoted_author_did == user_did:
                        print(f"   ✓ Self-quote (quoting own content)")
                    else:
                        print(f"   ✗ Quoting someone else's content")

        # Analyze reply status
        if is_reply:
            reply = record.reply
            root_uri = getattr(reply.root, "uri", "") if hasattr(reply, "root") else ""
            root_did = root_uri.split("/")[2] if "/" in root_uri else ""
            is_self_thread = root_did == user_did

            print(f"\n💬 Reply Analysis:")
            print(
                f"   Parent: {getattr(reply.parent, 'uri', 'N/A') if hasattr(reply, 'parent') else 'N/A'}"
            )
            print(f"   Root: {root_uri}")
            print(f"   Root author: {root_did}")

            if is_self_thread:
                print(f"   ✓ Self-reply (reply in own thread) → SYNCED")
            else:
                print(f"   ✗ Reply to someone else's thread → FILTERED")
        elif is_quote_post:
            print(f"\n📎 Quote Post:")
            if quoted_author_did and quoted_author_did != user_did:
                print(f"   ✗ Quoting someone else → SHOULD BE FILTERED")
            else:
                print(f"   ✓ Self-quote → SYNCED")
        else:
            print(f"\n📝 Root Post:")
            print(f"   ✓ Original post (not reply/quote) → SYNCED")

        # Check no-sync tag
        print(f"\n🏷️  Tag Check:")
        if has_no_sync_tag:
            print(f"   ✗ Contains #no-sync tag → SKIPPED")
        else:
            print(f"   ✓ No #no-sync tag → ELIGIBLE")

        # Check sync state
        print(f"\n💾 Sync State:")
        try:
            with open("sync_state.json", "r") as f:
                state = json.load(f)

            synced_entry = None
            for entry in state.get("synced_posts", []):
                if entry["bluesky_uri"] == post_uri:
                    synced_entry = entry
                    break

            if synced_entry:
                print(f"   ✓ Found in sync history")
                print(f"   Synced at: {synced_entry['synced_at']}")
                print(f"   Mastodon ID: {synced_entry['mastodon_id']}")
            else:
                # Check skipped posts
                skipped_entry = None
                for entry in state.get("skipped_posts", []):
                    if entry["bluesky_uri"] == post_uri:
                        skipped_entry = entry
                        break

                if skipped_entry:
                    print(f"   ⊘ Found in skipped posts")
                    print(f"   Reason: {skipped_entry['reason']}")
                    print(f"   Skipped at: {skipped_entry['skipped_at']}")
                else:
                    print(f"   ⊘ Not found in sync state (never processed)")
        except FileNotFoundError:
            print(f"   ⚠️  sync_state.json not found")

        return True

    except Exception as e:
        print(f"\n❌ Error fetching post: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Parse command line arguments and run investigation"""
    parser = argparse.ArgumentParser(
        description="Investigate Bluesky post sync status",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Investigate using post rkey (DID loaded from sync_state.json)
  python scripts/investigate_post.py 3m5x5kzlnoc2u
  
  # Investigate with custom DID
  python scripts/investigate_post.py 3m5x5kzlnoc2u did:plc:abc123xyz
  
  # Get rkey from Bluesky URL: https://bsky.app/profile/user/post/RKEY
        """,
    )

    parser.add_argument(
        "rkey", help="Post record key (the last part of Bluesky post URL)"
    )

    parser.add_argument(
        "did",
        nargs="?",
        help="User DID (optional, defaults to loading from sync_state.json)",
    )

    args = parser.parse_args()

    success = investigate_post(args.rkey, args.did)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
