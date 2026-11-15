import { MonthField } from '@/components/DatePicker'
import { PageHeader } from '@/components/PageHeader'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { GraduationTab } from '@/features/billing/components/finance/GraduationTab'
import { MonthlyTab } from '@/features/billing/components/finance/MonthlyTab'
import { useFinanceParams } from '@/features/billing/components/finance/useFinanceParams'
import type { FinanceTab } from '@/features/billing/components/finance/useFinanceParams'
import { useBillingOverview, useGraduationOverview } from '@/features/billing/hooks'
import { currentMonth } from '@/features/billing/labels'

// As mesmas classes das abas da ficha do aluno (pílula, ativa em verde-musgo)
const TRIGGER =
  'gap-1.5 rounded-full px-4 py-1.5 focus-visible:border-transparent focus-visible:ring-2 focus-visible:ring-ring/40 data-active:bg-sidebar-primary data-active:text-sidebar-primary-foreground data-active:hover:text-sidebar-primary-foreground dark:data-active:text-sidebar-primary-foreground'

// Página principal do app: o dinheiro do mês. Mensalidade e graduação em
// abas separadas (nunca se misturam); abre na Mensalidade, no mês atual.
export function FinancePage() {
  const { tab, filters, updateParams, listKey } = useFinanceParams()
  const overview = useBillingOverview(filters)
  const graduation = useGraduationOverview(filters.month)

  function setTab(value: string) {
    updateParams({
      aba: value === 'graduation' ? 'graduacao' : null,
      filtro: null,
      busca: null,
    })
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="Financeiro"
        actions={
          <MonthField
            aria-label="Mês"
            value={filters.month}
            onChange={(month) =>
              updateParams({ mes: month === currentMonth() ? null : month })
            }
            className="w-auto gap-3 rounded-full px-4"
          />
        }
      />

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="h-auto w-full max-w-full justify-start gap-1 rounded-full p-1 md:w-fit">
          <TabsTrigger value={'monthly' satisfies FinanceTab} className={`flex-1 ${TRIGGER}`}>
            Mensalidade
            {overview.data && <TabCount count={overview.data.unpaid_students} />}
          </TabsTrigger>
          <TabsTrigger value={'graduation' satisfies FinanceTab} className={`flex-1 ${TRIGGER}`}>
            Graduação
            {graduation.data && <TabCount count={graduation.data.unpaid_students} />}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="monthly" className="pt-2">
          <MonthlyTab
            overview={overview}
            filters={filters}
            listKey={listKey}
            updateParams={updateParams}
          />
        </TabsContent>
        <TabsContent value="graduation" className="pt-2">
          <GraduationTab overview={graduation} />
        </TabsContent>
      </Tabs>
    </div>
  )
}

// "· 8" ao lado do nome da aba: quantos ainda não pagaram
function TabCount({ count }: { count: number }) {
  return (
    <span className="text-status-critical group-data-active/tabs-trigger:text-sidebar-primary-foreground/80 in-data-active:text-sidebar-primary-foreground/80">
      · {count}
    </span>
  )
}
