import os
import json
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from google import genai


class ReviewType(Enum):
    QUICK = "quick"
    DETAILED = "detailed"
    SECURITY = "security"


@dataclass
class CodeReview:
    file_path: str
    issues: List[Dict]
    suggestions: List[Dict]
    quality_score: int
    summary: str


class AICodeReviewer:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY not found. Get one from https://makersuite.google.com/app/apikey"
            )

        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-1.5-pro"

    # ---------------- GEMINI CALL ---------------- #

    def _call_gemini(self, prompt: str) -> str:
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            raise Exception(f"Gemini API error: {e}")

    # ---------------- RESPONSE PARSER ---------------- #

    def _parse_response(self, response: str, file_path: str) -> CodeReview:
        try:
            clean = response.strip()

            if clean.startswith("```"):
                clean = clean.split("```")[1]

            data = json.loads(clean)

            return CodeReview(
                file_path=file_path,
                issues=data.get("issues", []),
                suggestions=data.get("suggestions", []),
                quality_score=data.get("quality_score", 0),
                summary=data.get("summary", ""),
            )

        except json.JSONDecodeError as e:
            return CodeReview(
                file_path=file_path,
                issues=[{
                    "type": "error",
                    "line": 0,
                    "message": f"JSON parsing failed: {e}",
                }],
                suggestions=[],
                quality_score=0,
                summary="Invalid Gemini response",
            )

    # ---------------- REVIEW ROUTER ---------------- #

    def review_code(
        self,
        code: str,
        file_path: str,
        review_type: ReviewType = ReviewType.DETAILED,
    ) -> CodeReview:
        if review_type == ReviewType.QUICK:
            return self._quick_review(code, file_path)
        if review_type == ReviewType.SECURITY:
            return self._security_review(code, file_path)
        return self._detailed_review(code, file_path)

    # ---------------- REVIEW TYPES ---------------- #

    def _quick_review(self, code: str, file_path: str) -> CodeReview:
        prompt = f"""
Review this code and provide a quick analysis.

File: {file_path}

Return ONLY valid JSON:
{{
  "issues": [{{"type":"security","line":10,"message":"desc","severity":"critical","cwe":"CWE-89"}}],
  "suggestions": [{{"category":"security","message":"fix","priority":"high"}}],
  "quality_score": 85,
  "summary": "security assessment"
}}
"""
        return self._parse_response(self._call_gemini(prompt), file_path)

    # ---------------- DIRECTORY REVIEW ---------------- #

    def review_directory(self, directory: str, extensions: List[str]) -> List[CodeReview]:
        reviews: List[CodeReview] = []

        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    path = os.path.join(root, file)
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            code = f.read()

                        review = self.review_code(code, path)
                        reviews.append(review)
                        print(f"✓ Reviewed {path}: {review.quality_score}/100")

                    except Exception as e:
                        print(f"✗ Error reviewing {path}: {e}")

        return reviews

    # ---------------- REPORT GENERATION ---------------- #

    def generate_report(self, reviews: List[CodeReview], output_file: str):
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# Code Review Report\n\n")
            f.write(f"Total files reviewed: {len(reviews)}\n\n")

            avg = sum(r.quality_score for r in reviews) / len(reviews) if reviews else 0
            f.write(f"Average Quality Score: {avg:.1f}/100\n\n")
            f.write("---\n\n")

            for review in reviews:
                f.write(f"## {review.file_path}\n\n")
                f.write(f"**Score:** {review.quality_score}/100\n\n")
                f.write(f"**Summary:** {review.summary}\n\n")

                if review.issues:
                    f.write("### Issues\n")
                    for issue in review.issues:
                        f.write(f"- {issue}\n")
                    f.write("\n")

                if review.suggestions:
                    f.write("### Suggestions\n")
                    for s in review.suggestions:
                        f.write(f"- {s}\n")
                    f.write("\n")

                f.write("---\n\n")

        print(f"\n✓ Report generated: {output_file}")


# ============================ CLI ============================ #

def main():
    import argparse

    parser = argparse.ArgumentParser(description="AI Code Reviewer")
    parser.add_argument("path", help="File or directory to review")
    parser.add_argument("--type", choices=["quick", "detailed", "security"], default="detailed")
    parser.add_argument("--output", default="review_report.md")
    parser.add_argument("--extensions", nargs="+")

    args = parser.parse_args()

    reviewer = AICodeReviewer()
    review_type = ReviewType(args.type)

    if os.path.isfile(args.path):
        with open(args.path, "r", encoding="utf-8") as f:
            code = f.read()

        review = reviewer.review_code(code, args.path, review_type)
        reviewer.generate_report([review], args.output)

        print("\n✓ Review complete")
        print(f"Score: {review.quality_score}/100")

    elif os.path.isdir(args.path):
        extensions = args.extensions or [".py", ".js", ".java", ".cpp", ".c", ".go", ".rs"]
        reviews = reviewer.review_directory(args.path, extensions)
        reviewer.generate_report(reviews, args.output)

        print("\n✓ Review complete")
        print(f"Files reviewed: {len(reviews)}")

    else:
        print("Invalid path")


if __name__ == "__main__":
    main()