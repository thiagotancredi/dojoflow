import { Check, MessageCircle } from 'lucide-react'
import { Link } from 'react-router'

import { BottomSheet, SheetBlock, SheetRow } from '@/components/BottomSheet'
import { Button } from '@/components/ui/button'
import type { BillingOverview, BillingOverviewItem } from '@/features/billing/api'
import { MonthBlocks } from '@/features/billing/components/finance/MonthBlocks'
import { dueIn, formatDayMonth } from '@/features/billing/labels'
import { formatMoney } from '@/lib/money'

// Celular: tocar no aluno abre este painel (o mesmo da lista de graduação)
export function MonthlySheet({
  item,
  onClose,
  onWhatsApp,
  onPay,
}: {
  item: BillingOverviewItem
  onClose: () => void
  onWhatsApp: () => void
  onPay: () => void
}) {
  const owes = Number(item.open_amount) > 0

  return (
    <BottomSheet
      title={item.name}
      subtitle={
        item.whatsapp_url
          ? item.responsible_name
            ? `Cobrança vai para ${item.responsible_name} (responsável)`
            : 'Cobrança vai para o próprio aluno'
          : owes
            ? 'Sem telefone para cobrar'
            : undefined
      }
      action={
        <Link
          to={`/app/alunos/${item.student_id}`}
          className="shrink-0 text-xs font-semibold whitespace-nowrap underline"
        >
          Ver ficha ›
        </Link>
      }
      onClose={onClose}
    >
      <SheetBlock title="Cobrança">
        <SheetRow label="Modalidade">{item.modalities.join(' · ')}</SheetRow>
        <SheetRow label="Em aberto">
          <span className={owes ? 'font-semibold text-status-pending' : undefined}>
            {formatMoney(item.open_amount)}
          </span>
        </SheetRow>
        {item.days_late !== null ? (
          <SheetRow label="Atraso">
            <span className="text-status-critical">
              {item.days_late} {item.days_late === 1 ? 'dia' : 'dias'}
            </span>
          </SheetRow>
        ) : (
          item.due_date && (
            <SheetRow label="Vencimento">
              {formatDayMonth(item.due_date)} ·{' '}
              <span className="text-muted-foreground">{dueIn(item.due_date)}</span>
            </SheetRow>
          )
        )}
      </SheetBlock>

      {owes && (
        <div className="grid grid-cols-2 gap-2">
          <Button
            variant="outline"
            className="h-11 rounded-full"
            disabled={!item.whatsapp_url}
            onClick={onWhatsApp}
          >
            <MessageCircle /> WhatsApp
          </Button>
          <Button className="h-11 rounded-full" onClick={onPay}>
            <Check /> Dar baixa
          </Button>
        </div>
      )}
    </BottomSheet>
  )
}

// Celular: "Ver resumo do mês" abre os 3 blocos, um embaixo do outro
export function MonthSummarySheet({
  data,
  onClose,
  onSeeAll,
}: {
  data: BillingOverview
  onClose: () => void
  onSeeAll: () => void
}) {
  return (
    <BottomSheet title="Resumo do mês" onClose={onClose}>
      <MonthBlocks data={data} onSeeAll={onSeeAll} className="lg:grid-cols-1" />
    </BottomSheet>
  )
}
