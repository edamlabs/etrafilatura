//! Exposes the pinned trafilatura-rs version, read from the workspace lockfile, as TRAFILATURA_ENGINE_VERSION.

use std::env;
use std::fs;
use std::path::PathBuf;

fn main() {
    let manifest =
        PathBuf::from(env::var("CARGO_MANIFEST_DIR").expect("cargo sets CARGO_MANIFEST_DIR"));
    let lock = manifest
        .ancestors()
        .map(|dir| dir.join("Cargo.lock"))
        .find(|path| path.is_file())
        .expect("Cargo.lock above the crate");
    println!("cargo:rerun-if-changed={}", lock.display());
    let text = fs::read_to_string(&lock).expect("readable Cargo.lock");
    // Line-based and trimmed: a Windows checkout turns the lockfile into CRLF.
    let version = text
        .split("[[package]]")
        .find(|block| {
            block
                .lines()
                .any(|line| line.trim() == "name = \"trafilatura\"")
        })
        .and_then(|block| {
            block
                .lines()
                .find_map(|line| line.trim().strip_prefix("version = \""))
        })
        .and_then(|rest| rest.strip_suffix('"'))
        .expect("trafilatura in Cargo.lock");
    println!("cargo:rustc-env=TRAFILATURA_ENGINE_VERSION={version}");
}
