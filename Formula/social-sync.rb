# Homebrew formula for Social Sync CLI
# https://docs.brew.sh/Formula-Cookbook
#
# Installation:
#   brew tap hossain-khan/social-sync
#   brew install social-sync
#
# Updating for a new release:
#   1. Update `version` to the new release tag
#   2. Update each `sha256` with the SHA-256 of the corresponding binary:
#      shasum -a 256 social-sync-macos-arm64
#      shasum -a 256 social-sync-macos-x86_64
#      shasum -a 256 social-sync-linux-x86_64
#      shasum -a 256 social-sync-linux-arm64

class SocialSync < Formula
  desc "Sync posts from Bluesky to Mastodon"
  homepage "https://github.com/hossain-khan/social-sync"
  license "MIT"
  version "0.9.1"

  # Pre-built binaries are attached to each GitHub Release by the
  # "Build Release Binaries" workflow (.github/workflows/build-binaries.yml).
  # Update the sha256 values below when releasing a new version.
  on_macos do
    on_arm do
      url "https://github.com/hossain-khan/social-sync/releases/download/#{version}/social-sync-macos-arm64"
      sha256 "ca298e2bf4fa0f2172a67071b246dc053a793b54bc82e41de9f06977f758019d"
    end

    on_intel do
      url "https://github.com/hossain-khan/social-sync/releases/download/#{version}/social-sync-macos-x86_64"
      sha256 "9e2264b8981af2033d8e0d73ae050b1a7debbbbe9a52245549111bdacd027882"
    end
  end

  on_linux do
    on_intel do
      url "https://github.com/hossain-khan/social-sync/releases/download/#{version}/social-sync-linux-x86_64"
      sha256 "48569a894f295cacd3b31c01d17689809e6b0b19987b7fbe981f94ee551bce43"
    end

    on_arm do
      url "https://github.com/hossain-khan/social-sync/releases/download/#{version}/social-sync-linux-arm64"
      sha256 "66f06295db66147a5fd377ec086d99ae8792fa29c85b9440f97cf3181b1de177"
    end
  end

  def install
    if OS.mac?
      arch_str = Hardware::CPU.arm? ? "arm64" : "x86_64"
      bin.install "social-sync-macos-#{arch_str}" => "social-sync"
    elsif OS.linux?
      arch_str = Hardware::CPU.arm? ? "arm64" : "x86_64"
      bin.install "social-sync-linux-#{arch_str}" => "social-sync"
    else
      odie "Unsupported operating system"
    end
  end

  test do
    assert_match "Social Sync", shell_output("#{bin}/social-sync --help")
  end
end
