"""
Custom validators for the school application
Provides validation for Arabic names, phone numbers, national IDs, etc.
"""

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
import re


class ArabicNameValidator:
    """Validates that a name contains only Arabic characters and spaces"""

    message = "الاسم يجب أن يحتوي على حروف عربية فقط"
    code = "invalid_arabic_name"

    def __init__(self, message=None, code=None):
        if message:
            self.message = message
        if code:
            self.code = code

    def __call__(self, value):
        if not value:
            return

        # Arabic Unicode range: \u0600-\u06FF
        # Allow Arabic letters, spaces, and common diacritics
        arabic_pattern = re.compile(r"^[\u0600-\u06FF\s\u064B-\u0652]+$")

        if not arabic_pattern.match(value):
            raise ValidationError(self.message, code=self.code)


class SaudiNationalIDValidator:
    """Validates Saudi national ID format (10 digits, starts with 1 or 2)"""

    message = "رقم الهوية الوطنية يجب أن يكون 10 أرقام ويبدأ بـ 1 أو 2"
    code = "invalid_national_id"

    def __call__(self, value):
        if not value:
            return

        # Remove any spaces or dashes
        clean_id = re.sub(r"[\s-]", "", value)

        # Check if 10 digits
        if not re.match(r"^\d{10}$", clean_id):
            raise ValidationError(self.message, code=self.code)

        # Check if starts with 1 or 2
        if not clean_id[0] in ["1", "2"]:
            raise ValidationError("رقم الهوية الوطنية يجب أن يبدأ بـ 1 أو 2", code=self.code)


class PhoneNumberValidator:
    """Validates Saudi phone number format"""

    message = "رقم الهاتف يجب أن يكون بصيغة صحيحة (05xxxxxxxx)"
    code = "invalid_phone"

    def __call__(self, value):
        if not value:
            return

        # Remove spaces, dashes, and parentheses
        clean_phone = re.sub(r"[\s\-\(\)]", "", value)

        # Remove country code if present
        clean_phone = re.sub(r"^(\+966|00966|966)", "0", clean_phone)

        # Saudi mobile numbers: 05xxxxxxxx (10 digits starting with 05)
        # Landline: 01xxxxxxx (9 digits starting with 01, 02, 03, 04)
        if not (re.match(r"^05\d{8}$", clean_phone) or re.match(r"^0[1-4]\d{7}$", clean_phone)):
            raise ValidationError(self.message, code=self.code)


class EmailDomainValidator:
    """Validates email domain (optional whitelist)"""

    def __init__(self, allowed_domains=None):
        self.allowed_domains = allowed_domains or []

    def __call__(self, value):
        if not value or not self.allowed_domains:
            return

        domain = value.split("@")[-1].lower()
        if domain not in self.allowed_domains:
            raise ValidationError(
                f"البريد الإلكتروني يجب أن ينتهي بأحد النطاقات: {', '.join(self.allowed_domains)}",
                code="invalid_email_domain",
            )


def validate_student_age(age):
    """Validate that student age is within reasonable range"""
    if age < 5 or age > 25:
        raise ValidationError("عمر الطالب يجب أن يكون بين 5 و 25 سنة", code="invalid_age")


def validate_grade_level(grade):
    """Validate grade level (1-12)"""
    if grade < 1 or grade > 12:
        raise ValidationError("المرحلة الدراسية يجب أن تكون بين 1 و 12", code="invalid_grade")


def validate_class_capacity(capacity):
    """Validate classroom capacity"""
    if capacity < 1 or capacity > 100:
        raise ValidationError("سعة الصف يجب أن تكون بين 1 و 100 طالب", code="invalid_capacity")


def validate_period_number(period):
    """Validate period number (1-8)"""
    if period < 1 or period > 8:
        raise ValidationError("رقم الحصة يجب أن يكون بين 1 و 8", code="invalid_period")


def validate_no_future_date(date):
    """Validate that date is not in the future"""
    from datetime import date as _date

    if date > _date.today():
        raise ValidationError("التاريخ لا يمكن أن يكون في المستقبل", code="future_date")


def validate_blood_type(blood_type):
    """Validate blood type format"""
    valid_types = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
    if blood_type and blood_type not in valid_types:
        raise ValidationError(
            f"فصيلة الدم غير صحيحة. الفصائل الصحيحة: {', '.join(valid_types)}",
            code="invalid_blood_type",
        )


# Pre-configured RegexValidators
saudi_phone_validator = RegexValidator(
    regex=r"^(05|01|02|03|04)\d{7,8}$",
    message="رقم الهاتف يجب أن يبدأ بـ 05 للجوال أو 01-04 للخط الأرضي",
    code="invalid_saudi_phone",
)

arabic_text_validator = RegexValidator(
    regex=r"^[\u0600-\u06FF\s\u064B-\u0652]+$",
    message="يجب أن يحتوي النص على حروف عربية فقط",
    code="invalid_arabic_text",
)

alphanumeric_arabic_validator = RegexValidator(
    regex=r"^[\u0600-\u06FF0-9\s\u064B-\u0652]+$",
    message="يجب أن يحتوي النص على حروف عربية وأرقام فقط",
    code="invalid_arabic_alphanumeric",
)
