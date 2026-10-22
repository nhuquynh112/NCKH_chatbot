from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from pathlib import Path
from typing import Any


STANDARD_PRODUCT_FIELDS = [
    "id",
    "slug",
    "sku",
    "name",
    "category",
    "brand",
    "price",
    "warranty_months",
    "description",
]

REQUIRED_RAW_FIELDS = ["id", "name", "category", "price"]


@dataclass(frozen=True)
class ProductValidationIssue:
    file_path: str
    product_ref: str
    field: str
    message: str
    severity: str = "warning"

    def format(self) -> str:
        return (
            f"{self.severity.upper()}: {self.file_path} | "
            f"{self.product_ref} | {self.field}: {self.message}"
        )


@dataclass(frozen=True)
class ProductRecord:
    id: str
    slug: str
    sku: str
    name: str
    category: str
    brand: str
    price: float
    warranty_months: int
    description: str
    specifications: dict[str, Any] = field(default_factory=dict)
    verification_status: str = "store_catalog_only"
    verified_at: str = ""
    source_urls: tuple[dict[str, str], ...] = field(default_factory=tuple)
    verification_note: str = ""
    source_file: str = ""

    @classmethod
    def from_raw(
        cls,
        raw: dict[str, Any],
        source_path: Path,
        index: int,
    ) -> tuple["ProductRecord", list[ProductValidationIssue]]:
        issues = validate_product_raw(raw, source_path, index)
        product_id = _safe_text(raw.get("id")) or f"row-{index}"
        sku = _safe_text(raw.get("sku")) or f"TC-PROD-{product_id}"

        return (
            cls(
                id=product_id,
                slug=_safe_text(raw.get("slug")) or sku,
                sku=sku,
                name=_safe_text(raw.get("name")),
                category=_safe_text(raw.get("category")),
                brand=_safe_text(raw.get("brand")),
                price=parse_price(raw.get("price")),
                warranty_months=parse_warranty(raw.get("warranty_months")),
                description=_safe_text(raw.get("description")),
                specifications=raw.get("specifications") if isinstance(raw.get("specifications"), dict) else {},
                verification_status=_safe_text(raw.get("verification_status")) or "store_catalog_only",
                verified_at=_safe_text(raw.get("verified_at")),
                source_urls=tuple(raw.get("source_urls") or []),
                verification_note=_safe_text(raw.get("verification_note")),
                source_file=str(source_path),
            ),
            issues,
        )

    def to_dict(self) -> dict[str, Any]:
        price_text = format_price_vnd(self.price)
        return {
            "id": self.id,
            "slug": self.slug,
            "sku": self.sku,
            "name": self.name,
            "category": self.category,
            "brand": self.brand,
            "price": price_text,
            "price_value": self.price,
            "warranty_months": self.warranty_months,
            "warranty": f"{self.warranty_months} tháng" if self.warranty_months else "",
            "description": self.description,
            "specifications": self.specifications,
            "use_case": self.description,
            "source_file": self.source_file,
            "verification_status": self.verification_status,
            "verified_at": self.verified_at,
            "source_urls": list(self.source_urls),
            "verification_note": self.verification_note,
        }


def load_product_records(path: Path) -> tuple[list[ProductRecord], list[ProductValidationIssue]]:
    if not path.exists():
        return [], [
            ProductValidationIssue(
                file_path=str(path),
                product_ref="file",
                field="path",
                message="File dữ liệu sản phẩm không tồn tại.",
                severity="error",
            )
        ]

    try:
        raw_data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [], [
            ProductValidationIssue(
                file_path=str(path),
                product_ref="file",
                field="json",
                message=f"JSON không hợp lệ: {exc}",
                severity="error",
            )
        ]

    if not isinstance(raw_data, list):
        return [], [
            ProductValidationIssue(
                file_path=str(path),
                product_ref="file",
                field="root",
                message="File sản phẩm phải là một JSON array.",
                severity="error",
            )
        ]

    products: list[ProductRecord] = []
    issues: list[ProductValidationIssue] = []
    for index, raw in enumerate(raw_data, start=1):
        if not isinstance(raw, dict):
            issues.append(
                ProductValidationIssue(
                    file_path=str(path),
                    product_ref=f"row {index}",
                    field="record",
                    message="Mỗi sản phẩm phải là object.",
                    severity="error",
                )
            )
            continue
        product, product_issues = ProductRecord.from_raw(raw, path, index)
        products.append(product)
        issues.extend(product_issues)

    return products, issues


def validate_product_raw(
    raw: dict[str, Any],
    source_path: Path,
    index: int,
) -> list[ProductValidationIssue]:
    product_ref = _safe_text(raw.get("sku")) or _safe_text(raw.get("id")) or f"row {index}"
    issues: list[ProductValidationIssue] = []

    for field_name in REQUIRED_RAW_FIELDS:
        if _is_missing(raw.get(field_name)):
            issues.append(
                ProductValidationIssue(
                    file_path=str(source_path),
                    product_ref=product_ref,
                    field=field_name,
                    message="Thiếu trường bắt buộc trong Product schema chuẩn.",
                    severity="error",
                )
            )

    for field_name in STANDARD_PRODUCT_FIELDS:
        if field_name in REQUIRED_RAW_FIELDS:
            continue
        if _is_missing(raw.get(field_name)):
            issues.append(
                ProductValidationIssue(
                    file_path=str(source_path),
                    product_ref=product_ref,
                    field=field_name,
                    message="Thiếu trường trong Product schema chuẩn; hệ thống dùng giá trị mặc định/an toàn.",
                    severity="warning",
                )
            )

    if not _is_missing(raw.get("price")) and parse_price(raw.get("price")) <= 0:
        issues.append(
            ProductValidationIssue(
                file_path=str(source_path),
                product_ref=product_ref,
                field="price",
                message="Giá sản phẩm không đọc được hoặc bằng 0.",
                severity="warning",
            )
        )

    return issues


def parse_price(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = _safe_text(value)
    if not text:
        return 0.0
    normalized = re.sub(r"[^\d.,]", "", text)
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(",", "")
    elif "," in normalized:
        normalized = normalized.replace(",", "")
    try:
        return float(normalized)
    except ValueError:
        digits = re.sub(r"\D", "", text)
        return float(digits) if digits else 0.0


def parse_warranty(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = _safe_text(value)
    match = re.search(r"\d+", text)
    return int(match.group(0)) if match else 0


def format_price_vnd(value: float) -> str:
    if value <= 0:
        return ""
    return f"{int(value):,} VNĐ".replace(",", ".")


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())
