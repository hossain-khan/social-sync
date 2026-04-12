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
  version "0.9.2"

  # Pre-built binaries are attached to each GitHub Release by the
  # "Build Release Binaries" workflow (.github/workflows/build-binaries.yml).
  # Update the sha256 values below when releasing a new version.
  on_macos do
    on_arm do
      url "https://github.com/hossain-khan/social-sync/releases/download/#{version}/social-sync-macos-arm64"
      sha256 "b49d91b78279beecd39928f61d2713dd9f8c1054c174af3869e32378d4c0e449"
    end

    on_intel do
      url "https://github.com/hossain-khan/social-sync/releases/download/#{version}/social-sync-macos-x86_64"
      sha256 "32fdd1fc3937978e6171978b4bc9530013ad1cadc16e6b706484720ea98fe4ca"
    end
  end

  on_linux do
    on_intel do
      url "https://github.com/hossain-khan/social-sync/releases/download/#{version}/social-sync-linux-x86_64"
      sha256 "963ed673d1c5610b5457b4c2bbd496548f3b67b2180303e89490e3a8f66f8f53"
    end

    on_arm do
      url "https://github.com/hossain-khan/social-sync/releases/download/#{version}/social-sync-linux-arm64"
      sha256 "646fd235ec0b2d2ae36df4ce260446ff1ea306f2679905e8d34b1621b53b717d"
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
