"""High-level repository architecture summary generator."""

from devpilot.repo.scanner import RepoScanResult


class RepoSummaryGenerator:
    """Generates human-readable and model-consumable repository overviews."""

    @staticmethod
    def generate(scan_result: RepoScanResult) -> str:
        lines = [
            "# Repository Architecture Summary",
            f"- **Root Path**: `{scan_result.repo_root}`",
            f"- **Total Tracked Files**: {scan_result.total_files}",
            f"- **Total Size**: {round(scan_result.total_size_bytes / 1024, 2)} KB",
        ]

        if scan_result.languages:
            sorted_langs = sorted(scan_result.languages.items(), key=lambda x: x[1], reverse=True)
            lang_str = ", ".join(f"{lang} ({count})" for lang, count in sorted_langs)
            lines.append(f"- **Languages**: {lang_str}")

        if scan_result.manifests:
            lines.append("- **Manifests & Build Files**:")
            for m in sorted(scan_result.manifests)[:10]:
                lines.append(f"  - `{m}`")

        if scan_result.entry_points:
            lines.append("- **Detected Entry Points**:")
            for ep in sorted(scan_result.entry_points)[:10]:
                lines.append(f"  - `{ep}`")

        lines.append("\n### Key Directory Structure")
        directories = set()
        for f in scan_result.files:
            parts = f.rel_path.split("/")
            if len(parts) > 1:
                directories.add(parts[0])
        for d in sorted(directories)[:15]:
            lines.append(f"- `/{d}`")

        return "\n".join(lines)
