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
  version "0.9.0"

  # Pre-built binaries are attached to each GitHub Release by the
  # "Build Release Binaries" workflow (.github/workflows/build-binaries.yml).
  # Update the sha256 values below when releasing a new version.
  on_macos do
    on_arm do
      url "https://github.com/hossain-khan/social-sync/releases/download/#{version}/social-sync-macos-arm64"
      sha256 "554b59700e0b2e1f531bc359337223d18c1f0a1f1bd20a3ea8f47ea84202a40d"
    end

    on_intel do
      url "https://github.com/hossain-khan/social-sync/releases/download/#{version}/social-sync-macos-x86_64"
      sha256 "db3e051452b885b5105ffc8ff931930440b9a6d0145bdb13be3e4fb91169923b"
    end
  end

  on_linux do
    on_intel do
      url "https://github.com/hossain-khan/social-sync/releases/download/#{version}/social-sync-linux-x86_64"
      sha256 "db638b1fc5a3573cd23c63065ab2dd114a4379879614bebe013e5ff110fb84b7"
    end

    on_arm do
      url "https://github.com/hossain-khan/social-sync/releases/download/#{version}/social-sync-linux-arm64"
      sha256 "9aebc1017412fb78ca209e0b2d316df577f772c472058ada8536608fec262c25"
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
