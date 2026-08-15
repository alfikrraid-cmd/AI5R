from dataclasses import replace

from .column_mapper import ColumnMapper
from .commit_engine import CommitEngine
from .dataset_analyzer import DatasetAnalyzer
from .document_classifier import DocumentClassifier
from .enterprise_object_detector import EnterpriseObjectDetector
from .import_pipeline import ImportPipeline
from .migration_session import MigrationSession
from .preview_engine import PreviewEngine
from .schema_detector import SchemaDetector
from .source_descriptor import SourceDescriptor
from .validation_engine import ValidationEngine


class MigrationOrchestrator:
    """Compose the canonical Enterprise Data Engine lifecycle."""

    __slots__ = (
        "_import_pipeline",
        "_analyzer",
        "_schema_detector",
        "_column_mapper",
        "_document_classifier",
        "_object_detector",
        "_validation_engine",
        "_preview_engine",
        "_commit_engine",
    )

    def __init__(
        self,
        *,
        import_pipeline: ImportPipeline,
        analyzer: DatasetAnalyzer,
        schema_detector: SchemaDetector,
        column_mapper: ColumnMapper,
        document_classifier: DocumentClassifier,
        object_detector: EnterpriseObjectDetector,
        validation_engine: ValidationEngine,
        preview_engine: PreviewEngine,
        commit_engine: CommitEngine,
    ) -> None:
        self._import_pipeline = import_pipeline
        self._analyzer = analyzer
        self._schema_detector = schema_detector
        self._column_mapper = column_mapper
        self._document_classifier = document_classifier
        self._object_detector = object_detector
        self._validation_engine = validation_engine
        self._preview_engine = preview_engine
        self._commit_engine = commit_engine

    def run(self, source: SourceDescriptor) -> MigrationSession:
        return self.commit(self.preview(source))

    def preview(self, source: SourceDescriptor) -> MigrationSession:
        import_result = self._import_pipeline.import_data(source)
        dataset = import_result.dataset
        analysis = self._analyzer.analyze(dataset)
        schemas = self._schema_detector.detect(dataset)
        column_mappings = self._column_mapper.map_columns(schemas)
        classifications = tuple(
            self._document_classifier.classify(schema, mapping)
            for schema, mapping in zip(schemas, column_mappings)
        )
        detected_objects = self._object_detector.detect(
            classifications,
            column_mappings,
            schemas,
        )
        validation = self._validation_engine.validate(
            detected_objects,
            schemas,
            column_mappings,
        )
        import_preview = self._preview_engine.preview(
            validation,
            detected_objects,
            schemas,
        )
        return MigrationSession(
            source=source,
            import_result=import_result,
            analysis=analysis,
            schemas=schemas,
            column_mappings=column_mappings,
            classifications=classifications,
            detected_objects=detected_objects,
            validation=validation,
            import_preview=import_preview,
            commit_result=None,
            status="PREVIEWED" if validation.is_valid else "INVALID",
        )

    def commit(self, session: MigrationSession) -> MigrationSession:
        result = self._commit_engine.commit(
            session.import_preview,
            session.validation,
            session.detected_objects,
        )
        return replace(
            session,
            commit_result=result,
            status=result.status,
        )

    def dry_run(self, source: SourceDescriptor) -> MigrationSession:
        session = self.preview(source)
        result = self._commit_engine.commit(
            session.import_preview,
            session.validation,
            session.detected_objects,
            dry_run=True,
        )
        return replace(
            session,
            commit_result=result,
            status=result.status,
        )

    def rollback(self, session: MigrationSession) -> MigrationSession:
        result = session.commit_result
        if (
            result is None
            or result.transaction_id is None
            or not result.rollback_available
        ):
            return replace(session, status="ROLLBACK_UNAVAILABLE")

        rolled_back = self._commit_engine.rollback(result.transaction_id)
        return replace(
            session,
            status="ROLLED_BACK" if rolled_back else "ROLLBACK_FAILED",
        )


__all__ = ["MigrationOrchestrator"]
