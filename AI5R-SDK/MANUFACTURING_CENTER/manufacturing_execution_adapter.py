from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from RUNTIME import RuntimeResponse, RuntimeStatus

from .manufacturing_result import ManufacturingResult
from .manufacturing_session import ManufacturingSession
from .manufacturing_status import ManufacturingStatus
from .manufacturing_step import ManufacturingStep


@dataclass(slots=True)
class ManufacturingExecutionAdapter:
    def adapt(
        self,
        *,
        response: RuntimeResponse,
        session: ManufacturingSession,
        step: ManufacturingStep,
    ) -> ManufacturingResult:
        self._validate(
            response=response,
            session=session,
            step=step,
        )

        runtime_metadata = dict(response.metadata)

        self._attach_runtime_metadata(
            target=session.metadata,
            response=response,
            runtime_metadata=runtime_metadata,
        )
        self._attach_runtime_metadata(
            target=step.metadata,
            response=response,
            runtime_metadata=runtime_metadata,
        )

        if response.status is RuntimeStatus.SUCCESS:
            return self._handle_success(
                response=response,
                session=session,
                step=step,
                runtime_metadata=runtime_metadata,
            )

        if response.status is RuntimeStatus.FAILED:
            return self._handle_failure(
                response=response,
                session=session,
                step=step,
                runtime_metadata=runtime_metadata,
            )

        raise ValueError(
            f"unsupported RuntimeStatus: {response.status!r}"
        )

    @staticmethod
    def _validate(
        *,
        response: RuntimeResponse,
        session: ManufacturingSession,
        step: ManufacturingStep,
    ) -> None:
        if not session.is_started:
            raise ValueError("session must be started")

        if session.is_terminal:
            raise ValueError("session must not be terminal")

        if step.status is not ManufacturingStatus.MANUFACTURING:
            raise ValueError(
                "step must be in MANUFACTURING status"
            )

        if not response.profile.strip():
            raise ValueError(
                "response.profile must not be empty"
            )

        if not response.definition.strip():
            raise ValueError(
                "response.definition must not be empty"
            )

    @staticmethod
    def _attach_runtime_metadata(
        *,
        target: dict[str, Any],
        response: RuntimeResponse,
        runtime_metadata: dict[str, Any],
    ) -> None:
        target["runtime_profile"] = response.profile
        target["runtime_definition"] = response.definition
        target["runtime_metadata"] = dict(runtime_metadata)

    def _handle_success(
        self,
        *,
        response: RuntimeResponse,
        session: ManufacturingSession,
        step: ManufacturingStep,
        runtime_metadata: dict[str, Any],
    ) -> ManufacturingResult:
        output = dict(response.output)
        artifact_paths = self._extract_artifacts(output)

        step.complete(output)

        session.transition(
            ManufacturingStatus.TESTING,
            stage=response.definition,
            progress=max(session.progress, 90),
        )

        result = session.complete()

        for path in artifact_paths:
            result.add_artifact(path)

        self._merge_without_overwrite(
            target=result.metadata,
            values=runtime_metadata,
        )
        result.metadata["runtime_profile"] = response.profile
        result.metadata["runtime_definition"] = response.definition
        result.metadata["runtime_metadata"] = dict(runtime_metadata)
        result.metadata["runtime_output"] = output

        return result

    def _handle_failure(
        self,
        *,
        response: RuntimeResponse,
        session: ManufacturingSession,
        step: ManufacturingStep,
        runtime_metadata: dict[str, Any],
    ) -> ManufacturingResult:
        error = self._require_error(response.error)

        step.fail(error)
        result = session.fail(error)

        self._merge_without_overwrite(
            target=result.metadata,
            values=runtime_metadata,
        )
        result.metadata["runtime_profile"] = response.profile
        result.metadata["runtime_definition"] = response.definition
        result.metadata["runtime_metadata"] = dict(runtime_metadata)

        return result

    @staticmethod
    def _require_error(error: str | None) -> str:
        if error is None:
            raise ValueError("response.error must not be empty")

        cleaned_error = error.strip()

        if not cleaned_error:
            raise ValueError("response.error must not be empty")

        return cleaned_error

    @staticmethod
    def _merge_without_overwrite(
        *,
        target: dict[str, Any],
        values: dict[str, Any],
    ) -> None:
        for key, value in values.items():
            target.setdefault(key, value)

    @staticmethod
    def _extract_artifacts(
        output: dict[str, Any],
    ) -> list[str]:
        if "artifacts" not in output:
            return []

        raw_artifacts = output["artifacts"]

        if isinstance(raw_artifacts, str):
            candidates: tuple[Any, ...] = (raw_artifacts,)
        elif isinstance(raw_artifacts, (list, tuple)):
            candidates = tuple(raw_artifacts)
        else:
            raise TypeError(
                "artifacts must be a str, list[str], "
                "or tuple[str, ...]"
            )

        artifacts: list[str] = []

        for candidate in candidates:
            if not isinstance(candidate, str):
                raise TypeError(
                    "artifact entries must be strings"
                )

            cleaned_path = candidate.strip()

            if cleaned_path:
                artifacts.append(cleaned_path)

        return artifacts
