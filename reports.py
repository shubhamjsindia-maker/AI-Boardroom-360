"""PDF summaries of saved scenarios and their meetings."""
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,KeepTogether
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from xml.sax.saxutils import escape

def pretty_financial_reference(metric_id):
    mapping={'proposal':'Investment Case','baseline':'Business as Usual','base_ebitda':'Core Business EBITDA',
             'incremental_ebitda':'Incremental EBITDA','incremental_wc_change':'Incremental Working Capital Requirement',
             'project_dscr':'Project Debt Service Coverage Ratio','pretax_profit':'Profit Before Tax',
             'closing_cash':'Closing Cash Balance','closing_debt':'Closing Total Borrowings',
             'operating_cash':'Operating Cash Flow','new_interest':'Interest on New Borrowing'}
    parts=str(metric_id).split('.')
    if len(parts)==3 and parts[1].startswith('Y'):
        title=mapping.get(parts[2],parts[2].replace('_',' ').title())
        return f'{mapping.get(parts[0],parts[0].title())} · Year {parts[1][1:]} · {title}'
    return str(metric_id).replace('_',' ').title()

def pdf_report(scenario,meeting):
    out=BytesIO();doc=SimpleDocTemplate(out,pagesize=(595,842),rightMargin=42,leftMargin=42,topMargin=38,bottomMargin=38)
    st=getSampleStyleSheet();st.add(ParagraphStyle(name='DocTitleX',parent=st['Heading1'],fontSize=19,leading=23,textColor=colors.HexColor('#14334B'),spaceAfter=10))
    st.add(ParagraphStyle(name='FineX',parent=st['Normal'],fontSize=8,leading=11,textColor=colors.HexColor('#576678')))
    story=[]
    def line(s,style='Normal'):
        story.append(Paragraph(escape(str(s)),st[style]));story.append(Spacer(1,7))
    line('AI Boardroom 360° | Decision-Support Report','DocTitleX')
    line('AI-GENERATED ANALYSIS — NOT A STATUTORY BOARD RESOLUTION','FineX')
    line(f"Company: {scenario['company']} | Scenario: #{scenario['id']} — {scenario['title']}")
    line('Financial forecast (INR lakh)','Heading2')
    rows=[['Year','Revenue','EBITDA','Pre-tax profit','Closing cash','Project DSCR']]
    for r in scenario['results']['proposal']:
        dscr=r['project_dscr'];rows.append([str(r['year']),*[f'{r[k]:,.2f}' for k in ['revenue','ebitda','pretax_profit','closing_cash']],('N/A' if dscr is None else f'{dscr:.2f}x')])
    t=Table(rows,repeatRows=1,colWidths=[42,88,79,105,96,100]);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#15344E')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#DFE5EB')),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),8)]));story.append(t);story.append(Spacer(1,15))
    m=meeting['meeting']
    line('Directors’ Advisory Voting Summary','Heading2')
    for role,vote in m.get('votes',{}).items():line(f'{role}: {vote}')
    line(f"Majority: {m.get('majority','Incomplete')} | AI mode: {m.get('mode','Unknown')}")
    line('Conditional recommendation','Heading2');line(m.get('recommendation','Incomplete meeting'))
    line(m.get('recommendation_rationale','Meeting did not finish.'))
    line('Director opinions and dissent','Heading2')
    for r in m.get('responses',[]):
        if r.get('round_number')==3:
            line(f"{r['agent_role']} ({r.get('vote','No vote')}): {r.get('position','')} ")
            for item in r.get('conditions',[])[:2]:line('Condition: '+item,'FineX')
    if m.get('chair_exchanges'):
        line('Chairperson follow-up questions','Heading2')
        for item in m['chair_exchanges']:
            line(f"Chair to {item['role']}: {item['question']}")
            line(f"Director: {item['answer']}")
            line('Supporting financial references: '+('; '.join(pretty_financial_reference(v) for v in item['supporting_metric_ids']) or 'None cited'),'FineX')
    line('Evidence and conditions','Heading2')
    for x in m.get('evidence_required',[]):line('• '+x)
    line('Limitations','Heading2')
    for x in m.get('limitations',['Financial forecasts and AI viewpoints may be inaccurate; verify independently.']):line('• '+x,'FineX')
    line('Prepared for educational demonstration. No authority to incur expenditure or resolve board matters is granted.','FineX')
    doc.build(story);return out.getvalue()
