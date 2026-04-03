#!/usr/bin/env python3
"""Parse coverage.xml and check threshold against changed files or overall."""
import xml.etree.ElementTree as ET
import sys
import os


def main():
    coverage_xml = os.environ.get("COVERAGE_XML", "coverage.xml")
    changed_src = os.environ.get("CHANGED_SRC_FILES", "").strip()
    repo_path = os.environ.get("REPO_PATH", "")
    threshold_str = os.environ.get("COVERAGE_THRESHOLD", "")

    if not threshold_str or threshold_str == "None":
        print("No coverage threshold configured — skipping check")
        return 0

    threshold = float(threshold_str)

    if not os.path.isfile(coverage_xml):
        print(f"ERROR: {coverage_xml} not found — cannot check coverage")
        return 1

    tree = ET.parse(coverage_xml)

    if changed_src:
        # Build set of changed file paths relative to service root
        changed_files = set()
        for f in changed_src.split("\n"):
            f = f.strip()
            if f and repo_path:
                changed_files.add(f.replace(repo_path + "/", "", 1))
            elif f:
                changed_files.add(f)

        total_stmts = 0
        total_hit = 0
        for cls in tree.findall(".//class"):
            fname = cls.attrib.get("filename", "")
            if fname in changed_files:
                lines = cls.findall(".//line")
                hits = sum(1 for ln in lines if int(ln.attrib.get("hits", 0)) > 0)
                total_stmts += len(lines)
                total_hit += hits

        if total_stmts > 0:
            cov = total_hit / total_stmts * 100
        else:
            cov = 100.0
        print(f"Changed-files coverage: {cov:.1f}% ({total_hit}/{total_stmts} lines)")
    else:
        rate = float(tree.getroot().attrib.get("line-rate", 0))
        cov = rate * 100
        print(f"Overall coverage: {cov:.1f}%")

    print(f"Threshold: {threshold:.0f}%")
    if cov < threshold:
        print(f"FAIL: Coverage {cov:.1f}% < threshold {threshold:.0f}%")
        return 1
    print(f"PASS: Coverage {cov:.1f}% >= threshold {threshold:.0f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
