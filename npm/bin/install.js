#!/usr/bin/env node

"use strict";

const https = require("https");
const fs = require("fs");
const path = require("path");
const os = require("os");
const { execSync } = require("child_process");

const TARGETS = {
  cursor: "armory-cursor.tar.gz",
  codex: "armory-codex.tar.gz",
  gemini: "armory-gemini.tar.gz",
};

const MAX_REDIRECTS = 3;

function parseArgs(argv) {
  const args = { target: null, dir: process.cwd(), repo: "Mathews-Tom/armory", tag: "latest" };
  for (let i = 2; i < argv.length; i++) {
    switch (argv[i]) {
      case "--target":
        args.target = argv[++i];
        break;
      case "--dir":
        args.dir = argv[++i];
        break;
      case "--repo":
        args.repo = argv[++i];
        break;
      case "--tag":
        args.tag = argv[++i];
        break;
      case "--help":
      case "-h":
        printUsage();
        process.exit(0);
      default:
        fatal(`Unknown argument: ${argv[i]}`);
    }
  }
  return args;
}

function printUsage() {
  process.stdout.write(
    [
      "Usage: armory-install --target <cursor|codex|gemini|claude> [options]",
      "",
      "Options:",
      "  --target <name>   Target platform (cursor, codex, gemini, claude)",
      "  --dir <path>      Extraction directory (default: cwd)",
      "  --repo <owner/name> GitHub repository (default: Mathews-Tom/armory)",
      "  --tag <tag>       Release tag (default: latest)",
      "  -h, --help        Show this help",
      "",
    ].join("\n")
  );
}

function fatal(msg) {
  process.stderr.write(`Error: ${msg}\n`);
  process.exit(1);
}

function download(url, dest, redirects) {
  return new Promise((resolve, reject) => {
    if (redirects > MAX_REDIRECTS) {
      return reject(new Error("Too many redirects"));
    }
    https
      .get(url, { headers: { "User-Agent": "armory-installer/0.1.0" } }, (res) => {
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          process.stderr.write(`  ↳ redirect ${res.statusCode}\n`);
          return resolve(download(res.headers.location, dest, redirects + 1));
        }
        if (res.statusCode === 404) {
          return reject(new Error(`Release asset not found (404). Verify the release tag and asset name exist at the repository.`));
        }
        if (res.statusCode !== 200) {
          return reject(new Error(`HTTP ${res.statusCode} from ${url}`));
        }

        const totalBytes = parseInt(res.headers["content-length"], 10) || 0;
        let downloaded = 0;
        const file = fs.createWriteStream(dest);

        res.on("data", (chunk) => {
          downloaded += chunk.length;
          if (totalBytes > 0) {
            const pct = ((downloaded / totalBytes) * 100).toFixed(0);
            process.stderr.write(`\r  downloading... ${pct}%`);
          } else {
            process.stderr.write(`\r  downloading... ${(downloaded / 1024).toFixed(0)} KB`);
          }
        });

        res.pipe(file);
        file.on("finish", () => {
          process.stderr.write("\n");
          file.close(resolve);
        });
        file.on("error", (err) => {
          fs.unlink(dest, () => {});
          reject(err);
        });
      })
      .on("error", reject);
  });
}

async function main() {
  const args = parseArgs(process.argv);

  if (!args.target) {
    fatal("--target is required. Use --help for usage.");
  }

  if (args.target === "claude") {
    process.stdout.write(
      "Claude Code uses skills directly. Install with:\n\n  npx skills add Mathews-Tom/armory\n\n"
    );
    process.exit(0);
  }

  if (!TARGETS[args.target]) {
    fatal(`Unknown target "${args.target}". Valid targets: cursor, codex, gemini, claude`);
  }

  const assetName = TARGETS[args.target];
  const releaseSegment =
    args.tag === "latest" ? "latest/download" : `download/${args.tag}`;
  const url = `https://github.com/${args.repo}/releases/${releaseSegment}/${assetName}`;
  const tmpFile = path.join(os.tmpdir(), `armory-${args.target}-${Date.now()}.tar.gz`);
  const destDir = path.resolve(args.dir);

  if (!fs.existsSync(destDir)) {
    fatal(`Directory does not exist: ${destDir}`);
  }

  process.stderr.write(`Downloading ${assetName} from ${args.repo}@${args.tag}\n`);

  try {
    await download(url, tmpFile, 0);
  } catch (err) {
    fatal(`Download failed: ${err.message}`);
  }

  process.stderr.write(`Extracting to ${destDir}\n`);

  try {
    execSync(`tar -xzf "${tmpFile}" -C "${destDir}"`, { stdio: "pipe" });
  } catch (err) {
    fs.unlink(tmpFile, () => {});
    fatal(`Extraction failed: ${err.message}`);
  }

  // Count extracted files by listing tarball contents
  let fileCount = 0;
  try {
    const listing = execSync(`tar -tzf "${tmpFile}"`, { encoding: "utf8" });
    fileCount = listing.split("\n").filter((l) => l.trim() && !l.endsWith("/")).length;
  } catch {
    fileCount = -1;
  }

  // Clean up tarball
  try {
    fs.unlinkSync(tmpFile);
  } catch {
    // non-critical
  }

  const countMsg = fileCount > 0 ? `${fileCount} files` : "files";
  process.stdout.write(`Done. Extracted ${countMsg} to ${destDir}\n`);
}

main();
