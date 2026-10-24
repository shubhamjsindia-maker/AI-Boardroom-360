"""Deterministic, simplified three-year financial forecasting model. All money INR lakh."""
from copy import deepcopy
from dataclasses import dataclass, asdict

@dataclass
class Inputs:
    revenue: float = 1000
    base_growth: float = 0.06
    baseline_ebitda_margin: float = 0.15
    cash: float = 80
    debt: float = 100
    interest_existing: float = 0.10
    receivable_days: float = 45
    inventory_days: float = 35
    payable_days: float = 30
    variable_cost_ratio: float = 0.55
    expansion_capex: float = 200
    loan_share: float = 0.70
    interest_new: float = 0.11
    term_years: int = 5
    expansion_sales_year1: float = 200
    expansion_growth: float = 0.10
    expansion_ebitda_margin: float = 0.25
    depreciation_years: int = 10
    income_tax_rate: float = 0.25  # simplified cash-tax proxy, not tax compliance
    existing_principal_per_year: float = 20
    capex_start_year: int = 1
    cancellation_pct: float = 0
    raw_material_inflation: float = 0
    interest_shock: float = 0


def validate(i: Inputs):
    errors=[]
    nonnegative=['revenue','cash','debt','expansion_capex','expansion_sales_year1','existing_principal_per_year','receivable_days','inventory_days','payable_days']
    for key in nonnegative:
        if getattr(i,key)<0: errors.append(f'{key} must be non-negative')
    for key in ['base_growth','baseline_ebitda_margin','variable_cost_ratio','expansion_growth','expansion_ebitda_margin','loan_share','income_tax_rate','cancellation_pct','raw_material_inflation']:
        val=getattr(i,key)
        if key in ('base_growth','expansion_growth'):
            if val <= -1 or val > 5: errors.append(f'{key} outside supported range')
        elif not 0<=val<=1: errors.append(f'{key} must be between 0 and 1')
    if i.term_years<1 or i.depreciation_years<1: errors.append('Loan term and depreciation life must be positive')
    if i.capex_start_year not in (1,2,3): errors.append('Capex start year must be 1, 2 or 3')
    if not 0<=i.interest_new<=1 or not 0<=i.interest_existing<=1 or not -1<=i.interest_shock<=1:
        errors.append('Unsupported interest rate')
    if i.interest_new+i.interest_shock<0: errors.append('Effective loan interest may not be negative')
    if i.existing_principal_per_year>i.debt: errors.append('Annual existing debt principal cannot exceed opening debt')
    if i.variable_cost_ratio>1-i.baseline_ebitda_margin: errors.append('Base variable costs exceed the amount available after baseline EBITDA')
    return errors


def wc(revenue, variable_cost, rec_days, inv_days, pay_days):
    return revenue*rec_days/365 + variable_cost*(inv_days-pay_days)/365


def simulate(i: Inputs, expansion=True):
    """Compare full-company 3-year forecast with business-as-usual.

    Working-capital changes are based on receivables, inventory and payables.
    Project DSCR is incremental CFADS / new-loan interest and principal, not firm-wide DSCR.
    Loan funding and capex occur at beginning of start year. Depreciation starts same year.
    """
    errors=validate(i)
    if errors: raise ValueError('; '.join(errors))
    result=[]
    prior_wc=wc(i.revenue, i.revenue*i.variable_cost_ratio, i.receivable_days,i.inventory_days,i.payable_days)
    base_wc=prior_wc
    cash=i.cash
    existing_debt=i.debt
    new_debt=0.0
    base_prior_revenue=i.revenue
    for year in range(1,4):
        base_revenue=i.revenue*(1+i.base_growth)**year
        base_ebitda=base_revenue*i.baseline_ebitda_margin
        base_variable=base_revenue*i.variable_cost_ratio
        base_next_wc=wc(base_revenue,base_variable,i.receivable_days,i.inventory_days,i.payable_days)
        base_wc_change=base_next_wc-base_wc
        base_wc=base_next_wc
        active=expansion and year>=i.capex_start_year
        n=year-i.capex_start_year
        incr_sales=(i.expansion_sales_year1*(1+i.expansion_growth)**n*(1-i.cancellation_pct)) if active else 0
        # Material shock applies to variable-cost base of incremental sales only.
        incr_ebitda=incr_sales*(i.expansion_ebitda_margin-i.variable_cost_ratio*i.raw_material_inflation)
        revenue=base_revenue+incr_sales
        ebitda=base_ebitda+incr_ebitda
        variable=base_variable+incr_sales*i.variable_cost_ratio*(1+i.raw_material_inflation)
        next_wc=wc(revenue,variable,i.receivable_days,i.inventory_days,i.payable_days)
        wc_change=next_wc-prior_wc
        prior_wc=next_wc
        started=active and year==i.capex_start_year
        capex=i.expansion_capex if started else 0.0
        loan_draw=capex*i.loan_share
        equity=capex-loan_draw
        new_debt+=loan_draw
        new_interest=new_debt*(i.interest_new+i.interest_shock) if active else 0.0
        new_principal=min(new_debt,i.expansion_capex*i.loan_share/i.term_years) if active else 0.0
        # Opening balance interest; principal paid at end of year.
        existing_interest=existing_debt*i.interest_existing
        existing_principal=min(existing_debt,i.existing_principal_per_year)
        depreciation=i.expansion_capex/i.depreciation_years if active and n<i.depreciation_years else 0
        pretax=ebitda-depreciation-existing_interest-new_interest
        cash_tax=max(0,pretax)*i.income_tax_rate
        operating_cash=ebitda-existing_interest-new_interest-cash_tax-wc_change
        change_cash=operating_cash-capex+loan_draw-existing_principal-new_principal
        cash+=change_cash
        # Proxy based on incremental income after estimated tax, WC change and before new debt service.
        incremental_wc=wc_change-base_wc_change
        incremental_tax=max(0,pretax)*i.income_tax_rate-max(0,base_ebitda-existing_interest)*i.income_tax_rate
        project_cfads=incr_ebitda-incremental_tax-incremental_wc
        project_service=new_interest+new_principal
        dscr=(project_cfads/project_service) if project_service>0 else None
        result.append(dict(year=year, revenue=revenue, base_revenue=base_revenue, incremental_revenue=incr_sales,
            ebitda=ebitda, base_ebitda=base_ebitda, incremental_ebitda=incr_ebitda, depreciation=depreciation,
            existing_interest=existing_interest,new_interest=new_interest, pretax_profit=pretax,cash_tax=cash_tax,
            working_capital_change=wc_change,incremental_wc_change=incremental_wc,
            operating_cash=operating_cash, capex=capex,loan_draw=loan_draw,equity_required=equity,
            existing_principal=existing_principal,new_principal=new_principal, closing_cash=cash,
            closing_debt=existing_debt-existing_principal+new_debt-new_principal,
            project_cfads=project_cfads,project_debt_service=project_service,project_dscr=dscr))
        existing_debt-=existing_principal
        new_debt-=new_principal
    return result


def compare(i: Inputs):
    base=simulate(i,False)
    project=simulate(i,True)
    return {'baseline':base,'proposal':project,'delta':[
        {k:round(p[k]-b[k],4) for k in ['revenue','ebitda','pretax_profit','operating_cash','closing_cash','closing_debt']}
        | {'year':p['year']} for p,b in zip(project,base)]}


def shocked(i:Inputs, kind:str, magnitude:float):
    v=deepcopy(i)
    if kind=='Customer orders cancelled': v.cancellation_pct=magnitude/100
    elif kind=='Raw material inflation': v.raw_material_inflation=magnitude/100
    elif kind=='Interest-rate increase': v.interest_shock=magnitude/100
    else: raise ValueError('Unsupported shock')
    if validate(v): raise ValueError('; '.join(validate(v)))
    return v


def metric_snapshot(c):
    vals={}
    for label in ['baseline','proposal']:
        for row in c[label]:
            for k,v in row.items():
                if isinstance(v,(float,int)) and k!='year': vals[f'{label}.Y{row["year"]}.{k}']=None if v is None else round(v,4)
    return vals
