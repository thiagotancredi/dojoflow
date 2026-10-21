"""Carga de demonstração de alunos e mensalidades (só no ambiente local).

Cria alunos de Taekwondo e Kickboxing com mensalidades de R$ 100 a R$ 200
em várias situações: pagas, parciais, atrasadas, a vencer, isentas, inativa,
menor de idade com responsável e aluno em duas modalidades.

Uso:
    poetry run python -m dojoflow.commands.seed_demo --academy-id 13 \\
        --contato "Ana Luiza=62900000001" --contato "Kennedy=62900000002"

    # Apaga só a carga (alunos com e-mail @demo.dojoflow.test) e cria de novo
    poetry run python -m dojoflow.commands.seed_demo --academy-id 13 \\
        --reset --contato ...

Telefones reais entram por --contato, para não ficarem no código. Alunos
fictícios ficam sem telefone (o WhatsApp não abre conversa com estranhos).
"""

import argparse
import asyncio
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.core.settings import settings
from dojoflow.database.session import AsyncSessionLocal, engine
from dojoflow.database.transaction import unit_of_work
from dojoflow.models.academy_modality import AcademyModality
from dojoflow.models.belt import Belt
from dojoflow.models.enrollment import Enrollment
from dojoflow.models.enrollment_belt import EnrollmentBelt
from dojoflow.models.modality import Modality
from dojoflow.models.payment import Payment
from dojoflow.models.payment_allocation import PaymentAllocation
from dojoflow.models.payment_transaction import PaymentTransaction
from dojoflow.models.responsible import Responsible
from dojoflow.models.student import Student
from dojoflow.models.student_responsible import StudentResponsible
from dojoflow.services.belt_rules import local_today
from dojoflow.services.billing import BillingService
from dojoflow.shared.enums import (
    EnrollmentStatus,
    PaymentMethod,
    StudentResponsibleRelationship,
    StudentSex,
)

DEMO_EMAIL_DOMAIN = 'demo.dojoflow.test'
TKD = 'Taekwondo'
KB = 'Kickboxing'


@dataclass
class Plan:
    """Uma matrícula da carga: modalidade, valor, dia e quando começou."""

    modality: str
    fee: str
    due_day: int
    enrolled_on: date
    # Taxa de matrícula: None = isenta
    enrollment_fee: str | None = None
    exempt: bool = False
    # Faixa atual: posição na sequência da modalidade (1 = primeira)
    belt_position: int = 1


@dataclass
class Profile:
    name: str
    plans: list[Plan]
    sex: StudentSex
    birth_date: date
    # Chave do --contato que dá o telefone (só os reais têm)
    contact: str | None = None
    # (nome, chave do --contato, parentesco) do responsável, para menores
    responsible: tuple[str, str | None, str] | None = None
    # Baixas na ordem: (valor, data, forma)
    payments: list[tuple[str, date, PaymentMethod]] = field(
        default_factory=list
    )
    inactive: bool = False


def d(day: str) -> date:
    return date.fromisoformat(day)


PIX = PaymentMethod.PIX
CASH = PaymentMethod.CASH
CARD = PaymentMethod.DEBIT_CARD

PROFILES = [
    # Atrasada em setembro e outubro (WhatsApp real)
    Profile(
        'Ana Luiza',
        [Plan(TKD, '150', 10, d('2026-08-05'), '80', belt_position=3)],
        StudentSex.FEMALE,
        d('1995-04-12'),
        contact='Ana Luiza',
        payments=[('80', d('2026-08-05'), PIX)],
    ),
    # Agosto pago, setembro parcial, outubro atrasado (WhatsApp real)
    Profile(
        'Kennedy',
        [Plan(KB, '180', 5, d('2026-07-01'), '100', belt_position=4)],
        StudentSex.MALE,
        d('1990-09-03'),
        contact='Kennedy',
        payments=[
            ('100', d('2026-07-01'), PIX),
            ('180', d('2026-08-04'), PIX),
            ('90', d('2026-09-10'), CASH),
        ],
    ),
    # Menor: a cobrança vai para o responsável (Kennedy)
    Profile(
        'Pedro Henrique',
        [Plan(TKD, '120', 10, d('2026-09-01'))],
        StudentSex.MALE,
        d('2014-06-20'),
        responsible=('Kennedy', 'Kennedy', 'father'),
    ),
    # Tudo pago
    Profile(
        'Lucas Almeida',
        [Plan(TKD, '100', 5, d('2026-05-20'), '50', belt_position=5)],
        StudentSex.MALE,
        d('2000-01-15'),
        payments=[
            ('150', d('2026-06-03'), PIX),
            ('100', d('2026-07-04'), PIX),
            ('100', d('2026-08-05'), PIX),
            ('100', d('2026-09-03'), PIX),
            ('100', d('2026-10-02'), PIX),
        ],
    ),
    # Setembro pago, outubro atrasado
    Profile(
        'Mariana Costa',
        [Plan(TKD, '130', 15, d('2026-08-10'), '70', belt_position=2)],
        StudentSex.FEMALE,
        d('1998-11-02'),
        payments=[('200', d('2026-09-14'), CARD)],
    ),
    # Em dia, outubro vence dia 25
    Profile(
        'Gabriel Rocha',
        [Plan(TKD, '200', 25, d('2026-07-15'), '100', belt_position=6)],
        StudentSex.MALE,
        d('1987-03-30'),
        payments=[
            ('100', d('2026-07-15'), PIX),
            ('200', d('2026-08-25'), PIX),
            ('200', d('2026-09-24'), PIX),
        ],
    ),
    # Matrícula nova: só a taxa em aberto; 1ª mensalidade em novembro
    Profile(
        'Beatriz Nunes',
        [Plan(TKD, '110', 28, d('2026-10-18'), '80')],
        StudentSex.FEMALE,
        d('2003-07-08'),
    ),
    # Três meses atrasados
    Profile(
        'Rafael Souza',
        [Plan(TKD, '160', 20, d('2026-06-18'), '80', belt_position=2)],
        StudentSex.MALE,
        d('1992-12-11'),
        payments=[('240', d('2026-07-19'), CASH)],
    ),
    # Isenta (bolsista)
    Profile(
        'Júlia Martins',
        [Plan(TKD, '0', 10, d('2026-03-10'), exempt=True, belt_position=7)],
        StudentSex.FEMALE,
        d('2008-05-25'),
        responsible=('Cláudia Martins', None, 'mother'),
    ),
    # Tudo pago
    Profile(
        'Carla Mendes',
        [Plan(KB, '170', 10, d('2026-08-20'), '90', belt_position=2)],
        StudentSex.FEMALE,
        d('1996-02-17'),
        payments=[
            ('260', d('2026-09-09'), PIX),
            ('170', d('2026-10-08'), PIX),
        ],
    ),
    # Outubro atrasado
    Profile(
        'Diego Ferreira',
        [Plan(KB, '190', 12, d('2026-07-10'), '90', belt_position=3)],
        StudentSex.MALE,
        d('1994-08-29'),
        payments=[
            ('280', d('2026-08-11'), PIX),
            ('190', d('2026-09-12'), CARD),
        ],
    ),
    # Em dia, outubro vence dia 27
    Profile(
        'Fernanda Lima',
        [Plan(KB, '140', 27, d('2026-08-25'), '70')],
        StudentSex.FEMALE,
        d('2001-10-05'),
        payments=[
            ('70', d('2026-08-25'), PIX),
            ('140', d('2026-09-26'), PIX),
        ],
    ),
    # Inativa com dívida antiga
    Profile(
        'Bruno Carvalho',
        [Plan(KB, '150', 15, d('2026-07-20'), '60', belt_position=2)],
        StudentSex.MALE,
        d('1989-01-21'),
        payments=[('60', d('2026-07-20'), CASH)],
        inactive=True,
    ),
    # Duas modalidades, as duas atrasadas em outubro
    Profile(
        'Eduarda Pires',
        [
            Plan(TKD, '120', 10, d('2026-09-02'), '60'),
            Plan(KB, '140', 10, d('2026-09-02'), '60'),
        ],
        StudentSex.FEMALE,
        d('1999-06-14'),
        payments=[('120', d('2026-09-02'), PIX)],
    ),
    # Em dia, outubro vence amanhã
    Profile(
        'Igor Batista',
        [Plan(KB, '200', 22, d('2026-08-01'), '100', belt_position=5)],
        StudentSex.MALE,
        d('1985-04-04'),
        payments=[
            ('100', d('2026-08-01'), PIX),
            ('200', d('2026-09-21'), PIX),
        ],
    ),
    # Menor com responsável sem telefone: WhatsApp desligado
    Profile(
        'Sofia Ramos',
        [Plan(TKD, '100', 5, d('2026-08-28'))],
        StudentSex.FEMALE,
        d('2016-02-09'),
        responsible=('Patrícia Ramos', None, 'mother'),
    ),
]


def first_of_next_month(day: date) -> date:
    if day.month == 12:  # noqa: PLR2004
        return date(day.year + 1, 1, 1)
    return date(day.year, day.month + 1, 1)


def demo_email(name: str) -> str:
    slug = name.lower().replace(' ', '.')
    return f'{slug}@{DEMO_EMAIL_DOMAIN}'


async def reset(session: AsyncSession, academy_id: int) -> int:
    """Apaga só os alunos da carga, com matrículas, cobranças e baixas."""
    students = select(Student.id).where(
        Student.academy_id == academy_id,
        Student.email.like(f'%@{DEMO_EMAIL_DOMAIN}'),
    )
    enrollments = select(Enrollment.id).where(
        Enrollment.student_id.in_(students)
    )
    transactions = select(PaymentTransaction.id).where(
        PaymentTransaction.student_id.in_(students)
    )
    total = len((await session.scalars(students)).all())

    await session.execute(
        delete(PaymentAllocation).where(
            PaymentAllocation.payment_transaction_id.in_(transactions)
        )
    )
    await session.execute(
        delete(PaymentTransaction).where(
            PaymentTransaction.id.in_(transactions)
        )
    )
    await session.execute(
        delete(Payment).where(Payment.enrollment_id.in_(enrollments))
    )
    await session.execute(
        delete(EnrollmentBelt).where(
            EnrollmentBelt.enrollment_id.in_(enrollments)
        )
    )
    await session.execute(
        delete(Enrollment).where(Enrollment.id.in_(enrollments))
    )
    await session.execute(
        delete(StudentResponsible).where(
            StudentResponsible.student_id.in_(students)
        )
    )
    await session.execute(
        delete(Responsible).where(
            Responsible.academy_id == academy_id,
            Responsible.email.like(f'%@{DEMO_EMAIL_DOMAIN}'),
        )
    )
    await session.execute(delete(Student).where(Student.id.in_(students)))
    return total


async def modality_ids(session: AsyncSession, academy_id: int) -> dict:
    rows = await session.execute(
        select(Modality.name, Modality.id)
        .join(AcademyModality, AcademyModality.modality_id == Modality.id)
        .where(
            AcademyModality.academy_id == academy_id,
            Modality.name.in_([TKD, KB]),
        )
    )
    found = dict(rows.tuples().all())
    missing = {TKD, KB} - set(found)
    if missing:
        raise SystemExit(
            f'A academia não oferece: {", ".join(sorted(missing))}.'
        )
    return found


async def belt_id(
    session: AsyncSession, academy_id: int, modality_id: int, position: int
) -> int | None:
    belts = (
        await session.scalars(
            select(Belt.id)
            .where(
                Belt.academy_id == academy_id, Belt.modality_id == modality_id
            )
            .order_by(Belt.position)
        )
    ).all()
    if not belts:
        return None
    return belts[min(position, len(belts)) - 1]


async def seed(  # noqa: PLR0914
    session: AsyncSession,
    academy_id: int,
    contacts: dict[str, str],
) -> int:
    today = local_today()
    billing = BillingService(session)
    modalities = await modality_ids(session, academy_id)
    responsibles: dict[str, int] = {}

    for profile in PROFILES:
        student = Student(
            academy_id=academy_id,
            name=profile.name,
            phone=contacts.get(profile.contact or ''),
            phone_is_whatsapp=True if profile.contact in contacts else None,
            email=demo_email(profile.name),
            birth_date=profile.birth_date,
            sex=profile.sex,
        )
        session.add(student)
        await session.flush()

        if profile.responsible:
            name, contact, relationship = profile.responsible
            if name not in responsibles:
                responsible = Responsible(
                    academy_id=academy_id,
                    name=name,
                    phone=contacts.get(contact or '', ''),
                    phone_is_whatsapp=contact in contacts,
                    email=demo_email(f'resp {name}'),
                )
                session.add(responsible)
                await session.flush()
                responsibles[name] = responsible.id
            session.add(
                StudentResponsible(
                    academy_id=academy_id,
                    student_id=student.id,
                    responsible_id=responsibles[name],
                    relationship=StudentResponsibleRelationship(relationship),
                )
            )

        enrollment_ids = []
        for plan in profile.plans:
            modality_id = modalities[plan.modality]
            enrollment = Enrollment(
                academy_id=academy_id,
                student_id=student.id,
                modality_id=modality_id,
                status=EnrollmentStatus.ACTIVE,
                monthly_fee=None if plan.exempt else Decimal(plan.fee),
                due_day=None if plan.exempt else plan.due_day,
                is_exempt=plan.exempt,
                billing_start_month=(
                    None
                    if plan.exempt
                    else first_of_next_month(plan.enrolled_on)
                ),
                created_at=datetime.combine(
                    plan.enrolled_on, datetime.min.time(), tzinfo=UTC
                ),
            )
            session.add(enrollment)
            await session.flush()
            enrollment_ids.append(enrollment.id)
            await billing.create_enrollment_fee(
                academy_id,
                enrollment.id,
                Decimal(plan.enrollment_fee) if plan.enrollment_fee else None,
                plan.enrolled_on,
            )

            belt = await belt_id(
                session, academy_id, modality_id, plan.belt_position
            )
            if belt is not None:
                session.add(
                    EnrollmentBelt(
                        academy_id=academy_id,
                        enrollment_id=enrollment.id,
                        belt_id=belt,
                        graduated_on=plan.enrolled_on,
                    )
                )

        # Mensalidades até hoje; depois as baixas, da mais antiga à mais nova
        await billing.ensure_monthly_charges(academy_id, today)
        for amount, paid_on, method in profile.payments:
            await billing.create_payment(
                academy_id, student.id, Decimal(amount), paid_on, method, None
            )

        if profile.inactive:
            for enrollment_id in enrollment_ids:
                enrollment = await session.get_one(Enrollment, enrollment_id)
                enrollment.status = EnrollmentStatus.INACTIVE
        await session.flush()

    return len(PROFILES)


def parse_contacts(values: list[str]) -> dict[str, str]:
    contacts = {}
    for value in values:
        name, _, phone = value.partition('=')
        if not name or not phone:
            raise SystemExit(f'Use --contato "Nome=62999990000" ({value!r}).')
        contacts[name.strip()] = ''.join(ch for ch in phone if ch.isdigit())
    return contacts


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--academy-id', type=int, required=True)
    parser.add_argument('--contato', action='append', default=[])
    parser.add_argument('--reset', action='store_true')
    args = parser.parse_args()

    if settings.ENVIRONMENT != 'dev':
        raise SystemExit(
            'A carga de demonstração só roda com ENVIRONMENT=dev.'
        )

    contacts = parse_contacts(args.contato)

    try:
        async with AsyncSessionLocal() as session:
            async with unit_of_work(session):
                existing = await session.scalar(
                    select(Student.id).where(
                        Student.academy_id == args.academy_id,
                        Student.email.like(f'%@{DEMO_EMAIL_DOMAIN}'),
                    )
                )
                if args.reset:
                    removed = await reset(session, args.academy_id)
                    print(f'{removed} aluno(s) da carga anterior apagado(s).')
                elif existing is not None:
                    raise SystemExit(
                        'A carga já existe nesta academia. Use --reset para '
                        'apagar e criar de novo.'
                    )
                created = await seed(session, args.academy_id, contacts)
            print(f'{created} aluno(s) criados na academia {args.academy_id}.')
    finally:
        await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
