import factory


class OnboardingPayloadFactory(factory.DictFactory):
    academy_name = factory.Sequence(lambda number: f'Academia Teste {number}')
    master_name = factory.Faker('name', locale='pt_BR')
    telegram_user_id = factory.Sequence(lambda number: 100000000 + number)
    phone = factory.Sequence(lambda number: f'6299999{number:04d}')
