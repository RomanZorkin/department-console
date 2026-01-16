from pathlib import Path

import pandas as pd
from pydantic import BaseModel, ValidationError

from app.models import AnalyticRecord, OrganizationRecord


class CSVLoader:
    """Загрузчик и валидатор CSV файлов.

    Поддерживает загрузку различных типов CSV файлов с валидацией через
    Pydantic модели.
    """

    @staticmethod
    def load_analytic_data(path: Path | None = None) -> pd.DataFrame:
        """Загрузить CSV с аналитикой и провалидировать каждую строку.

        Args:
            path: Путь к CSV файлу. Если не указан, используется
                ``app/data/analytic/data.csv``.

        Returns:
            DataFrame с валидированными данными через AnalyticRecord.
        """
        if path is None:
            path = (
                Path(__file__).resolve().parent.parent / "data" / "analytic" / "data.csv"
            )

        df = pd.read_csv(path)

        try:
            # Возвращаем DataFrame, соответствующий списку валидных Pydantic‑моделей.
            records = [AnalyticRecord.model_validate(record) for record in df.to_dict("records")]
        except ValidationError as exc:
            # Перебрасываем исключение с дополнительным контекстом
            raise ValueError(
                f"Ошибка валидации данных в {path}: {exc}",
            ) from exc

        # Преобразуем обратно в DataFrame; столбцы и их типы определяются
        # Pydantic‑моделью AnalyticRecord.
        valid_df = pd.DataFrame([r.model_dump() for r in records])
        return valid_df

    @staticmethod
    def load_organizations_data(path: Path | None = None) -> pd.DataFrame:
        """Загрузить CSV с данными об организациях и провалидировать каждую строку.

        Args:
            path: Путь к CSV файлу. Если не указан, используется
                ``app/data/analytic/organizations.csv``.

        Returns:
            DataFrame с валидированными данными через OrganizationRecord.
        """
        if path is None:
            path = (
                Path(__file__).resolve().parent.parent / "data" / "analytic" / "organizations.csv"
            )

        df = pd.read_csv(path)

        # Добавляем расчетные колонки
        df["staffing"] = df["by_list"] / df["by_staff"]
        df["cash_use"] = df["cash_execution"] / df["buget_limits"]
        df["serviceability"] = (df["equipment"] - df["faulty_equipment"]) / df["equipment"]

        # Вычисляем value как минимальное значение из трех колонок
        df["value"] = df[["staffing", "cash_use", "serviceability"]].min(axis=1)

        # Сохраняем расчетные колонки для последующего добавления
        calculated_cols = df[["staffing", "cash_use", "serviceability", "value"]].copy()

        try:
            # Валидируем только те колонки, которые есть в OrganizationRecord

            # (исключаем расчетные колонки, так как модель их не принимает из-за extra="forbid")
            org_cols = [
                "city",
                "region",
                "by_staff",
                "by_list",
                "buget_limits",
                "cash_execution",
                "equipment",
                "faulty_equipment",
            ]
            records = [
                OrganizationRecord.model_validate(record)
                for record in df[org_cols].to_dict(orient="records")
            ]
        except ValidationError as exc:
            # Перебрасываем исключение с дополнительным контекстом
            raise ValueError(
                f"Ошибка валидации данных в {path}: {exc}",
            ) from exc

        # Преобразуем обратно в DataFrame; столбцы и их типы определяются
        # Pydantic‑моделью OrganizationRecord.
        valid_df = pd.DataFrame([r.model_dump() for r in records])

        # Добавляем расчетные колонки обратно после валидации
        valid_df["staffing"] = calculated_cols["staffing"]
        valid_df["cash_use"] = calculated_cols["cash_use"]
        valid_df["serviceability"] = calculated_cols["serviceability"]
        valid_df["value"] = calculated_cols["value"]

        return valid_df

    @staticmethod
    def load_csv(
        path: Path,
        model: type[BaseModel],
        model_name: str | None = None,
    ) -> pd.DataFrame:
        """Универсальный метод для загрузки CSV с валидацией через Pydantic модель.

        Args:
            path: Путь к CSV файлу.
            model: Pydantic модель для валидации записей.
            model_name: Имя модели для сообщений об ошибках.
                Если не указано, используется имя класса модели.

        Returns:
            DataFrame с валидированными данными.
        """
        df = pd.read_csv(path)

        model_name = model_name or model.__name__

        try:
            records = [model.model_validate(record) for record in df.to_dict("records")]
        except ValidationError as exc:
            # Перебрасываем исключение с дополнительным контекстом
            raise ValueError(
                f"Ошибка валидации данных в {path} для модели {model_name}: {exc}",
            ) from exc

        valid_df = pd.DataFrame([r.model_dump() for r in records])
        return valid_df
