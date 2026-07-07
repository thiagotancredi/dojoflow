from enum import StrEnum


class TelegramFlow(StrEnum):
    ONBOARDING = 'onboarding'
    STUDENT_CREATION = 'student_creation'
    STUDENT_SEARCH = 'student_search'
    STUDENT_EDIT = 'student_edit'


class TelegramStep(StrEnum):
    WAITING_ACADEMY_NAME = 'waiting_academy_name'
    WAITING_MASTER_NAME = 'waiting_master_name'

    WAITING_STUDENT_NAME = 'waiting_student_name'
    WAITING_STUDENT_MODALITY = 'waiting_student_modality'
    WAITING_STUDENT_SEX = 'waiting_student_sex'

    WAITING_STUDENT_RESPONSIBLE_TYPE = 'waiting_student_responsible_type'
    WAITING_STUDENT_RESPONSIBLE_RELATIONSHIP = (
        'waiting_student_responsible_relationship'
    )
    WAITING_STUDENT_RESPONSIBLE_NAME = 'waiting_student_responsible_name'
    WAITING_STUDENT_RESPONSIBLE_PHONE = 'waiting_student_responsible_phone'
    WAITING_STUDENT_RESPONSIBLE_IS_WHATSAPP = (
        'waiting_student_responsible_is_whatsapp'
    )
    WAITING_STUDENT_RESPONSIBLE_EMAIL = 'waiting_student_responsible_email'
    WAITING_STUDENT_RESPONSIBLE_NEXT_ACTION = (
        'waiting_student_responsible_next_action'
    )

    WAITING_STUDENT_RESPONSIBLE_CHOICE = (
        'waiting_student_responsible_choice'
    )
    WAITING_STUDENT_RESPONSIBLE_REFERENCE_SEARCH = (
        'waiting_student_responsible_reference_search'
    )

    WAITING_STUDENT_ADDRESS_CHOICE = 'waiting_student_address_choice'
    WAITING_STUDENT_ADDRESS_REFERENCE_SEARCH = (
        'waiting_student_address_reference_search'
    )
    WAITING_STUDENT_ADDRESS_ZIP_CODE = 'waiting_student_address_zip_code'
    WAITING_STUDENT_ADDRESS_STREET = 'waiting_student_address_street'
    WAITING_STUDENT_ADDRESS_NEIGHBORHOOD = (
        'waiting_student_address_neighborhood'
    )
    WAITING_STUDENT_ADDRESS_NUMBER = 'waiting_student_address_number'
    WAITING_STUDENT_ADDRESS_COMPLEMENT = 'waiting_student_address_complement'

    WAITING_STUDENT_PHONE = 'waiting_student_phone'
    WAITING_STUDENT_EMAIL = 'waiting_student_email'
    WAITING_STUDENT_IS_WHATSAPP = 'waiting_student_is_whatsapp'
    WAITING_STUDENT_CPF = 'waiting_student_cpf'
    WAITING_STUDENT_INSTAGRAM = 'waiting_student_instagram'
    WAITING_STUDENT_BIRTH_DATE = 'waiting_student_birth_date'
    WAITING_STUDENT_MONTHLY_FEE = 'waiting_student_monthly_fee'
    WAITING_STUDENT_DUE_DAY = 'waiting_student_due_day'
    WAITING_STUDENT_IS_EXEMPT = 'waiting_student_is_exempt'
    WAITING_STUDENT_FIELD_CONFIRMATION = (
        'waiting_student_field_confirmation'
    )
    WAITING_STUDENT_CONFIRMATION = 'waiting_student_confirmation'

    WAITING_STUDENT_SEARCH_NAME = 'waiting_student_search_name'

    WAITING_STUDENT_EDIT_MENU = 'waiting_student_edit_menu'
    WAITING_STUDENT_EDIT_BASIC_DATA = 'waiting_student_edit_basic_data'
    WAITING_STUDENT_EDIT_ADDRESS_MENU = 'waiting_student_edit_address_menu'
    WAITING_STUDENT_EDIT_ADDRESS_REFERENCE_SEARCH = (
        'waiting_student_edit_address_reference_search'
    )
    WAITING_STUDENT_EDIT_ADDRESS_ZIP_CODE = (
        'waiting_student_edit_address_zip_code'
    )
    WAITING_STUDENT_EDIT_ADDRESS_STREET = (
        'waiting_student_edit_address_street'
    )
    WAITING_STUDENT_EDIT_ADDRESS_NEIGHBORHOOD = (
        'waiting_student_edit_address_neighborhood'
    )
    WAITING_STUDENT_EDIT_ADDRESS_NUMBER = (
        'waiting_student_edit_address_number'
    )
    WAITING_STUDENT_EDIT_ADDRESS_COMPLEMENT = (
        'waiting_student_edit_address_complement'
    )
    WAITING_STUDENT_EDIT_FIELD_CONFIRMATION = (
        'waiting_student_edit_field_confirmation'
    )
    WAITING_STUDENT_EDIT_MONTHLY_FEE_MENU = (
        'waiting_student_edit_monthly_fee_menu'
    )
    WAITING_STUDENT_EDIT_NAME = 'waiting_student_edit_name'
    WAITING_STUDENT_EDIT_MODALITY = 'waiting_student_edit_modality'
    WAITING_STUDENT_EDIT_SEX = 'waiting_student_edit_sex'
    WAITING_STUDENT_EDIT_CPF = 'waiting_student_edit_cpf'
    WAITING_STUDENT_EDIT_INSTAGRAM = 'waiting_student_edit_instagram'
    WAITING_STUDENT_EDIT_BIRTH_DATE = 'waiting_student_edit_birth_date'
    WAITING_STUDENT_EDIT_EMAIL = 'waiting_student_edit_email'
    WAITING_STUDENT_EDIT_MONTHLY_FEE = (
        'waiting_student_edit_monthly_fee'
    )
    WAITING_STUDENT_EDIT_DUE_DAY = 'waiting_student_edit_due_day'
    WAITING_STUDENT_EDIT_CONFIRMATION = (
        'waiting_student_edit_confirmation'
    )

    COMPLETED = 'completed'
