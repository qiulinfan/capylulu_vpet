from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


PIPELINE = Path(__file__).resolve().parent
PET = PIPELINE.parents[3]
ROOT = PET.parents[1]
QA = PET / "qa" / "action-gifs"
REVIEW_NAME = "visual-review.json"
VALIDATION_NAME = "validation.json"
BUILD_NAME = "build.py"
PROMOTION_RECEIPT = PIPELINE / "promotion-receipt.json"
REVIEW_ARTIFACTS = (
    "right-preview.gif",
    "left-preview.gif",
    "right-contact-sheet.png",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_frame_names(direction: str) -> set[str]:
    state = f"running-{direction}"
    return {f"{state}-{number:02d}.png" for number in range(1, 9)}


def stage_candidate(staging: Path) -> None:
    evidence = staging / "evidence"
    evidence.mkdir()
    for name in (REVIEW_NAME, VALIDATION_NAME, BUILD_NAME, *REVIEW_ARTIFACTS):
        source = PIPELINE / name
        if not source.is_file():
            raise FileNotFoundError(source)
        (evidence / name).write_bytes(source.read_bytes())

    for direction in ("right", "left"):
        state = f"running-{direction}"
        expected = expected_frame_names(direction)
        source_directory = PIPELINE / direction
        observed = {path.name for path in source_directory.glob("*.png")}
        if observed != expected:
            raise ValueError(
                f"{state} lineage frame set differs: "
                f"observed={sorted(observed)}, expected={sorted(expected)}"
            )
        destination = staging / state
        destination.mkdir()
        for name in sorted(expected):
            (destination / name).write_bytes((source_directory / name).read_bytes())


def verified_staged_evidence(
    staging: Path,
) -> tuple[dict[str, object], dict[str, object]]:
    evidence = staging / "evidence"
    review = json.loads((evidence / REVIEW_NAME).read_text(encoding="utf-8"))
    validation = json.loads((evidence / VALIDATION_NAME).read_text(encoding="utf-8"))
    if review.get("status") != "pass" or review.get("errors") != []:
        raise ValueError("visual review is not a clean pass")
    if validation.get("ok") is not True or validation.get("errors") != []:
        raise ValueError("machine validation is not a clean pass")
    if validation.get("build_sha256") != sha256(evidence / BUILD_NAME):
        raise ValueError(
            "machine validation was not produced by the staged build implementation"
        )
    if validation.get("face_geometry_sha256") != sha256(PIPELINE / "face_geometry.py"):
        raise ValueError("machine validation used a different face-geometry analyzer")
    if validation.get("manifest_sha256") != sha256(PET / "official-frames-v1-manifest.json"):
        raise ValueError("official manifest changed after machine validation")

    output_hashes = validation.get("output_sha256")
    if not isinstance(output_hashes, dict):
        raise ValueError("machine validation does not bind its output artifacts")
    for direction in ("right", "left"):
        state = f"running-{direction}"
        staged_directory = staging / state
        observed = {
            path.name: sha256(path) for path in sorted(staged_directory.glob("*.png"))
        }
        if observed != review.get(f"{direction}_frame_sha256"):
            raise ValueError(f"visual review is stale for staged {direction} frames")
        if observed != output_hashes.get(f"{direction}_frames"):
            raise ValueError(f"machine validation is stale for staged {direction} frames")

    observed_artifacts = {
        name: sha256(evidence / name) for name in REVIEW_ARTIFACTS
    }
    if observed_artifacts != review.get("artifact_sha256"):
        raise ValueError("visual review is stale for staged review artifacts")
    if observed_artifacts != output_hashes.get("artifacts"):
        raise ValueError("machine validation is stale for staged review artifacts")

    source_sheet = PET / str(validation.get("source_sheet", ""))
    alpha_sheet = PET / str(validation.get("alpha_sheet", ""))
    if (
        not source_sheet.is_file()
        or sha256(source_sheet) != validation.get("source_sheet_sha256")
    ):
        raise ValueError("selected source sheet no longer matches machine validation")
    if (
        not alpha_sheet.is_file()
        or sha256(alpha_sheet) != validation.get("alpha_sheet_sha256")
    ):
        raise ValueError("selected alpha sheet no longer matches machine validation")
    gold_hashes = validation.get("identity_authority_sha256")
    if not isinstance(gold_hashes, dict) or not gold_hashes:
        raise ValueError("machine validation does not bind the six gold authorities")
    for relative, expected in gold_hashes.items():
        path = PET / relative
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"gold authority changed after validation: {relative}")
    return review, validation


def restore_qa(snapshot: dict[str, bytes]) -> None:
    QA.mkdir(parents=True, exist_ok=True)
    for path in QA.iterdir():
        if path.is_file():
            path.unlink()
    for name, data in snapshot.items():
        (QA / name).write_bytes(data)


def promote() -> None:
    with tempfile.TemporaryDirectory(
        prefix="lulu-directional-promotion-", dir=PET
    ) as temporary:
        staging = Path(temporary)
        stage_candidate(staging)
        review, validation = verified_staged_evidence(staging)

        official_backups: dict[Path, bytes] = {}
        qa_backup = {
            path.name: path.read_bytes() for path in QA.iterdir() if path.is_file()
        }
        previous_receipt = (
            PROMOTION_RECEIPT.read_bytes() if PROMOTION_RECEIPT.is_file() else None
        )
        try:
            for direction in ("right", "left"):
                state = f"running-{direction}"
                official = PET / "official-frames-v1" / state
                for staged in sorted((staging / state).glob("*.png")):
                    target = official / staged.name
                    official_backups[target] = target.read_bytes()
                    target.write_bytes(staged.read_bytes())

            subprocess.run(
                ["uv", "run", "--frozen", "python", "tools/build_action_gifs.py"],
                cwd=ROOT,
                check=True,
            )
            qa_validation = json.loads(
                (QA / "validation.json").read_text(encoding="utf-8")
            )
            if qa_validation.get("ok") is not True or qa_validation.get("errors") != []:
                raise ValueError("rebuilt action-GIF validation is not a clean pass")

            promoted_hashes: dict[str, dict[str, str]] = {}
            for direction in ("right", "left"):
                state = f"running-{direction}"
                staged_directory = staging / state
                official = PET / "official-frames-v1" / state
                staged_hashes = {
                    path.name: sha256(path)
                    for path in sorted(staged_directory.glob("*.png"))
                }
                official_hashes = {
                    path.name: sha256(path)
                    for path in sorted(official.glob("*.png"))
                }
                if official_hashes != staged_hashes:
                    raise ValueError(f"official {state} differs after promotion")
                promoted_hashes[state] = official_hashes
                qa_action = qa_validation.get("actions", {}).get(state, {})
                if qa_action.get("source_frame_sha256") != list(staged_hashes.values()):
                    raise ValueError(f"QA GIF does not consume the promoted {state} frames")

            receipt = {
                "ok": True,
                "status": "promoted",
                "visual_review_sha256": sha256(staging / "evidence" / REVIEW_NAME),
                "machine_validation_sha256": sha256(
                    staging / "evidence" / VALIDATION_NAME
                ),
                "build_sha256": validation["build_sha256"],
                "promoted_frame_sha256": promoted_hashes,
                "qa_validation_sha256": sha256(QA / "validation.json"),
                "qa_gif_sha256": {
                    path.name: sha256(path) for path in sorted(QA.glob("*.gif"))
                },
                "review_status": review["status"],
                "errors": [],
            }
            receipt_path = staging / "promotion-receipt.json"
            receipt_path.write_text(
                json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            PROMOTION_RECEIPT.write_bytes(receipt_path.read_bytes())
        except BaseException:
            for path, data in official_backups.items():
                path.write_bytes(data)
            restore_qa(qa_backup)
            if previous_receipt is None:
                if PROMOTION_RECEIPT.exists():
                    PROMOTION_RECEIPT.unlink()
            else:
                PROMOTION_RECEIPT.write_bytes(previous_receipt)
            raise

    print("Promoted 16 reviewed frames and rebuilt all action GIFs: OK")


if __name__ == "__main__":
    promote()
