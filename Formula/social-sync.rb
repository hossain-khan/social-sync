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
  version "0.10.0"

  # Pre-built binaries are attached to each GitHub Release by the
  # "Build Release Binaries" workflow (.github/workflows/build-binaries.yml).
  # Update the sha256 values below when releasing a new version.
  on_macos do
    on_arm do
      url "https://github.com/hossain-khan/social-sync/releases/download/#{version}/social-sync-macos-arm64"
      sha256 "a4f38a3f2840dd21dd9f4db4f0fc4d7302b2089289d7e3f7b8322b5806e02666"
    end

    on_intel do
      url "https://github.com/hossain-khan/social-sync/releases/download/#{version}/social-sync-macos-x86_64"
      sha256 "624192e229cef755f0b6eed78353f121e088914be8a22fb330684280e59050c8"
    end
  end

  on_linux do
    on_intel do
      url "https://github.com/hossain-khan/social-sync/releases/download/#{version}/social-sync-linux-x86_64"
      sha256 "b3cbad4036625ab3e04f9ccee694f656155d2224bdf59120194b6f475a1b2950"
    end

    on_arm do
      url "https://github.com/hossain-khan/social-sync/releases/download/#{version}/social-sync-linux-arm64"
      sha256 "6ebb96fea9c315de65242606235867fa7934f9c58e24bf12e53aa309e8a3c53c"
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
