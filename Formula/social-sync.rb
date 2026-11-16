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
  version "0.11.0"

  # Pre-built binaries are attached to each GitHub Release by the
  # "Build Release Binaries" workflow (.github/workflows/build-binaries.yml).
  # Update the sha256 values below when releasing a new version.
  on_macos do
    on_arm do
      url "https://github.com/hossain-khan/social-sync/releases/download/#{version}/social-sync-macos-arm64"
      sha256 "3813930b194602b12376fcd83fc3173f659edba3e9cf126c8ded9b846f732982"
    end

    on_intel do
      url "https://github.com/hossain-khan/social-sync/releases/download/#{version}/social-sync-macos-x86_64"
      sha256 "c570b9ab4a304182c03221b70f7ea39890072634d9740308cb017f1d2a07b09f"
    end
  end

  on_linux do
    on_intel do
      url "https://github.com/hossain-khan/social-sync/releases/download/#{version}/social-sync-linux-x86_64"
      sha256 "bf2cadd435d61a199ccd7c9feff2d7adfcb71f91ae5643cde943314f3b633ae4"
    end

    on_arm do
      url "https://github.com/hossain-khan/social-sync/releases/download/#{version}/social-sync-linux-arm64"
      sha256 "16f6188f747095f0488a42c59a5697c72cde4f6e0e39b6b50b2c5551d97a0e03"
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
