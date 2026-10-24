"""AI Boardroom 360° — streamlit MVP. Run: streamlit run app.py"""
import os
import hmac
from dataclasses import asdict
import pandas as pd
import plotly.express as px
import streamlit as st
from finance import Inputs,compare,shocked,validate
from data import sample_inputs,template_bytes,parse_workbook,NAME
from store import save_scenario,get_scenario,list_scenarios,save_meeting,get_meeting,list_meetings,add_chair_exchange
from board import conduct_board,chair_question,ROLES
from reports import pdf_report

st.set_page_config(page_title='AI Boardroom 360°',page_icon='🏛️',layout='wide')

# IMPORTANT: This is a single-operator demo application. All sessions share one
# SQLite database; production multi-tenant deployment needs user-specific storage.
def _configured_secret(name):
    value = os.environ.get(name)
    if value:
        return value
    try:
        return st.secrets.get(name)
    except (FileNotFoundError, KeyError):
        return None

password = _configured_secret('BOARDROOM_PASSWORD')
if not password:
    st.error('Website is not configured: set BOARDROOM_PASSWORD in deployment secrets. This app does not allow anonymous access to shared financial data.')
    st.info('See DEPLOY.md for Streamlit Community Cloud and Docker deployment instructions.')
    st.stop()

if not st.session_state.get('authenticated', False):
    st.title('🏛️ AI Boardroom 360°')
    st.caption('Private demonstration website · Password required')
    with st.form('login'):
        supplied = st.text_input('Access password', type='password')
        submit = st.form_submit_button('Enter Boardroom', type='primary')
    if submit:
        if hmac.compare_digest(supplied, str(password)):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error('Incorrect access password.')
    st.stop()

api_key = _configured_secret('OPENAI_API_KEY')
if api_key:
    os.environ['OPENAI_API_KEY'] = str(api_key)
gemini_key = _configured_secret('GEMINI_API_KEY')
if gemini_key:
    os.environ['GEMINI_API_KEY'] = str(gemini_key)
st.markdown('''<style>
[data-testid="stSidebar"] {background:#14283d} [data-testid="stSidebar"] * {color:#f6f8fb!important}
.block-container {padding-top:1.3rem;max-width:1350px} h1,h2,h3 {color:#15344e!important}
div[data-testid="stMetric"] {background:#f3f7fa;border:1px solid #dfe9ed;padding:12px;border-radius:12px}
</style>''',unsafe_allow_html=True)
if 'company' not in st.session_state:st.session_state.company=NAME
if 'inputs' not in st.session_state:st.session_state.inputs=asdict(sample_inputs())
if 'scenario_id' not in st.session_state:st.session_state.scenario_id=None
if 'meeting_id' not in st.session_state:st.session_state.meeting_id=None

with st.sidebar:
    st.title('🏛️ Boardroom 360°')
    st.caption('Simulate · Debate · Decide')
    page=st.radio('Navigate',['Overview','Data Studio','Digital Twin','AI Boardroom','Shock Engine','Reports'])
    st.divider()
    st.caption(f"Company: {st.session_state.company}")
    st.caption('Private demonstration · INR lakh')
    if st.button('Log out'):
        st.session_state.authenticated = False
        st.rerun()
    st.info('Simulated advisory analysis, not a statutory board decision.')

scenario=get_scenario(st.session_state.scenario_id) if st.session_state.scenario_id else None
meeting=get_meeting(st.session_state.meeting_id) if st.session_state.meeting_id else None

def figure(rows):
    df=pd.DataFrame(rows)
    return px.line(df,x='year',y=['revenue','ebitda','closing_cash'],markers=True,title='Three-year forecast (₹ lakh)',labels={'value':'₹ lakh','year':'Projection year','variable':'Metric'})

def load_scenario_options(label='Saved scenario'):
    vals=list_scenarios()
    if not vals:st.warning('Save a scenario in the Digital Twin first.');return None
    ids=[r[0] for r in vals]
    default=ids.index(st.session_state.scenario_id) if st.session_state.scenario_id in ids else 0
    selected=st.selectbox(label,ids,index=default,format_func=lambda v:next(f'#{r[0]} · {r[2]} · {r[1]}' for r in vals if r[0]==v))
    if st.session_state.scenario_id!=selected:
        st.session_state.scenario_id=selected;st.session_state.meeting_id=None
    return get_scenario(selected)

if page=='Overview':
    st.title('Executive Overview')
    st.caption('Business performance and decision scenarios')
    i=Inputs(**st.session_state.inputs);c=compare(i)
    a,b,c1,d=st.columns(4)
    a.metric('Annual revenue',f'₹{i.revenue:,.0f}L');b.metric('EBITDA',f'₹{i.revenue*i.baseline_ebitda_margin:,.0f}L')
    c1.metric('Opening cash',f'₹{i.cash:,.0f}L');d.metric('Existing borrowing',f'₹{i.debt:,.0f}L')
    st.plotly_chart(figure(c['proposal']),use_container_width=True)
    st.subheader('Recent scenarios')
    r=list_scenarios()
    if r:st.dataframe(pd.DataFrame(r,columns=['ID','Company','Scenario','Created (UTC)','Parent scenario']),hide_index=True,use_container_width=True)
    else:st.info('Use Data Studio to load a sample, then create a scenario in Digital Twin.')

elif page=='Data Studio':
    st.title('Business Data Studio')
    tab1,tab2=st.tabs(['Demo company','Excel import'])
    with tab1:
        st.subheader(NAME)
        st.write('Synthetic manufacturing company with ₹1,000 lakh historical revenue, ₹150 lakh EBITDA and ₹80 lakh cash.')
        st.download_button('Download complete sample workbook',template_bytes(),'Nova_Manufacturing_Template.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        if st.button('Load demo company',type='primary'):
            st.session_state.company=NAME;st.session_state.inputs=asdict(sample_inputs());st.session_state.scenario_id=None;st.session_state.meeting_id=None
            st.success('Sample company loaded.')
    with tab2:
        st.write('Only the supplied `.xlsx` template is accepted. Amounts must be in **INR lakh**.')
        upload=st.file_uploader('Upload standardized financial workbook',type=['xlsx'])
        if upload is not None and upload.size > 5 * 1024 * 1024:
            st.error('Workbook exceeds the 5 MB upload limit.')
            st.stop()
        if upload is not None:
            try:
                name,inputs,warnings=parse_workbook(upload.getvalue())
                st.success(f'Workbook validated for {name}')
                st.dataframe(pd.DataFrame([asdict(inputs)]),hide_index=True)
                for w in warnings:st.warning(w)
                if st.button('Use validated upload',type='primary'):
                    st.session_state.company=name;st.session_state.inputs=asdict(inputs);st.session_state.scenario_id=None;st.session_state.meeting_id=None
                    st.success('Imported company is active.')
            except Exception as e:st.error(f'Upload rejected: {e}')

elif page=='Digital Twin':
    st.title('Business Digital Twin')
    st.caption('Create a three-year financial scenario and save an immutable snapshot before convening the board.')
    i=Inputs(**st.session_state.inputs)
    with st.form('scenario_form'):
        title=st.text_input('Scenario title','₹2 crore manufacturing expansion')
        x,y,z=st.columns(3)
        with x:
            i.expansion_capex=st.number_input('Investment capex (₹ lakh)',0.0,100000.0,float(i.expansion_capex),step=25.0)
            i.expansion_sales_year1=st.number_input('Incremental year-1 sales (₹ lakh)',0.0,100000.0,float(i.expansion_sales_year1),step=25.0)
            i.expansion_growth=st.slider('Expansion annual growth (%)',-50,100,int(i.expansion_growth*100))/100
            i.expansion_ebitda_margin=st.slider('Incremental EBITDA margin (%)',0,80,int(i.expansion_ebitda_margin*100))/100
        with y:
            i.loan_share=st.slider('New debt funding (%)',0,100,int(i.loan_share*100))/100
            i.interest_new=st.slider('New loan interest (%)',0,30,int(i.interest_new*100))/100
            i.term_years=st.number_input('Loan repayment term (years)',1,30,int(i.term_years))
            i.depreciation_years=st.number_input('Asset useful life (years)',1,40,int(i.depreciation_years))
        with z:
            i.base_growth=st.slider('Organic sales growth (%)',-40,60,int(i.base_growth*100))/100
            i.receivable_days=st.number_input('Receivable days',0.0,365.0,float(i.receivable_days))
            i.inventory_days=st.number_input('Inventory days',0.0,365.0,float(i.inventory_days))
            i.payable_days=st.number_input('Payable days',0.0,365.0,float(i.payable_days))
            i.capex_start_year=st.selectbox('Expansion begins in year',[1,2,3],index=i.capex_start_year-1)
        submitted=st.form_submit_button('Calculate & Save Scenario',type='primary')
    if submitted:
        errors=validate(i)
        if errors:
            for e in errors:st.error(e)
        else:
            res=compare(i)
            sid=save_scenario(st.session_state.company,title,asdict(i),res)
            st.session_state.inputs=asdict(i);st.session_state.scenario_id=sid;st.session_state.meeting_id=None
            st.success(f'Scenario #{sid} saved. Ready for the boardroom.')
    if st.session_state.scenario_id:
        s=get_scenario(st.session_state.scenario_id)
        st.subheader(f'Calculated results · Scenario #{s["id"]}')
        st.dataframe(pd.DataFrame(s['results']['proposal']).round(2),hide_index=True,use_container_width=True)
        st.plotly_chart(figure(s['results']['proposal']),use_container_width=True)
        st.subheader('Incremental impact vs business as usual')
        st.dataframe(pd.DataFrame(s['results']['delta']).round(2),hide_index=True,use_container_width=True)
        st.caption('The model uses simplified tax assumptions. Project DSCR excludes legacy debt service and is not a complete corporate covenant model.')

elif page=='AI Boardroom':
    st.title('AI Boardroom · Five Director Debate')
    s=load_scenario_options()
    if s:
        col1,col2=st.columns([2,1])
        with col1:
            mode=st.radio('Meeting mode',['Demo / offline','Live Gemini API','Live OpenAI API'],horizontal=True)
        default_model='gemini-2.5-flash-lite' if mode=='Live Gemini API' else 'gpt-4.1-mini'
        with col2:
            model=st.text_input('API model name',value=default_model,key='gemini_model' if mode=='Live Gemini API' else 'openai_model')
        if mode=='Live Gemini API':
            if gemini_key:
                st.success('Gemini API key found. You can test the connection before convening the board.')
            else:
                st.warning('Add GEMINI_API_KEY in Streamlit → Manage app → Settings → Secrets. Never upload keys to GitHub.')
            st.caption('Gemini free-tier eligibility and limits vary by model and project. A full three-round meeting makes 15 model calls.')
            if st.button('Test Gemini connection',disabled=not bool(gemini_key)):
                try:
                    from board import gemini_generate
                    with st.spinner('Checking Gemini with one small request...'):
                        reply=gemini_generate('Reply as a JSON object with an ok boolean.',{'test':'Reply with {"ok":true}'},model)
                    if reply.get('ok') is True:
                        st.success('Gemini responded successfully! You can convene the board.')
                    else:
                        st.warning('Gemini responded but did not follow the test format. Try another model.')
                except Exception as exc:
                    st.error(f'Gemini test failed: {exc}')
        elif mode=='Live OpenAI API':
            if api_key:
                st.success('OpenAI API key configured. Live meetings use billed API usage.')
            else:
                st.warning('Add OPENAI_API_KEY in Streamlit → Manage app → Settings → Secrets.')
            if st.button('Test OpenAI connection',disabled=not bool(api_key)):
                try:
                    from openai import OpenAI
                    with st.spinner('Checking API access...'):
                        OpenAI(api_key=str(api_key), timeout=20, max_retries=0).models.retrieve(model.strip())
                    st.success('OpenAI model is accessible.')
                except Exception as exc:
                    message=str(exc)
                    if '401' in message or 'invalid_api_key' in message:
                        st.error('OpenAI authentication failed (401). Check OPENAI_API_KEY.')
                    elif '429' in message or 'insufficient_quota' in message:
                        st.error('OpenAI quota or rate limit reached (429). Check API billing.')
                    else:
                        st.error(f'OpenAI connection failed: {type(exc).__name__}. Verify model and API settings.')
        else:
            st.info('Offline demo uses simulated director opinions and does not require an API key.')
        if st.button('Convene Board Meeting',type='primary'):
            try:
                with st.spinner('Running three structured debate rounds...'):
                    result=conduct_board(s['results'],mode,model)
                mid=save_meeting(s['id'],result,mode);st.session_state.meeting_id=mid
                if result['complete']:st.success(f'Meeting #{mid} completed; 15 director responses including five advisory votes.')
                else:
                    st.error('Meeting incomplete: '+'; '.join(result['errors']))
                    st.info('No final votes have been counted. Review the message above before retrying.')
            except Exception as e:st.error(f'Unable to run board: {e}')
        m=get_meeting(st.session_state.meeting_id) if st.session_state.meeting_id else None
        if m and m['scenario_id']==s['id']:
            result=m['meeting']
            for rnd in [1,2,3]:
                with st.expander(f'Round {rnd}: '+['Independent assessment','Challenges and counterarguments','Revised positions and advisory voting'][rnd-1],expanded=rnd==3):
                    for r in result.get('responses',[]):
                        if r['round_number']!=rnd:continue
                        st.markdown(f'**{r["agent_role"]}** '+(f'· **{r["vote"]}**' if r.get('vote') else ''))
                        st.write(r['position'])
                        if r.get('key_arguments'):
                            st.write('**Reasoning:** ' + '; '.join(r['key_arguments']))
                        if r.get('conditions') and rnd==3:
                            st.write('**Conditions:** ' + '; '.join(r['conditions']))
                        with st.expander('Technical metric references'):
                            st.caption(', '.join(r.get('supporting_metric_ids',[])))
                        if r.get('challenge_question'):st.info(f"Challenge to {r.get('challenge_to')}: {r['challenge_question']}")
            st.subheader('Advisory voting — five directors')
            st.caption('Each vote is an advisory opinion based on this scenario. Voting is completed in Round 3; it is not interactive shareholder voting.')
            votes=result.get('votes',{})
            for director in ROLES:
                vote=votes.get(director,'PENDING')
                symbol={'APPROVE':'✅','REJECT':'❌','DEFER':'⏸️'}.get(vote,'⚪')
                st.markdown(f'**{director}** — {symbol} **{vote}**')
            counts=result.get('counts',{})
            if counts:
                a,b,c=st.columns(3)
                a.metric('Approve',counts.get('APPROVE',0))
                b.metric('Reject',counts.get('REJECT',0))
                c.metric('Defer',counts.get('DEFER',0))
            st.metric('Majority',result.get('majority','INCOMPLETE'))
            # Render the message directly; never pass Streamlit display objects
            # to st.write(), which exposes internal DeltaGenerator documentation.
            if result['complete']:
                st.success(result.get('recommendation', 'Meeting completed.'))
            else:
                st.warning(result.get('recommendation', 'Meeting incomplete.'))
            st.caption(result.get('recommendation_rationale',''))
            if result['complete']:
                st.divider()
                st.subheader('Challenge the Board · Chairperson Questions')
                st.caption('Follow-up answers do not alter the closed advisory votes. Use Shock Engine to change financial assumptions and reconvene.')
                with st.form('chair_question_form'):
                    director=st.selectbox('Ask a director',list(ROLES.keys()))
                    question=st.text_area('Your question',placeholder='What evidence would make you change your recommendation?',max_chars=1000)
                    ask=st.form_submit_button('Ask Director',type='primary')
                if ask:
                    try:
                        with st.spinner('Preparing evidence-based director response...'):
                            exchange=chair_question(s['results'],result,director,question,mode=m['mode'],model=model)
                        updated=add_chair_exchange(m['id'],exchange)
                        st.success('Chairperson question saved with this meeting.')
                        result=updated
                    except Exception as exc: st.error(f'Unable to answer: {exc}')
                for exchange in result.get('chair_exchanges',[]):
                    with st.chat_message('user'):
                        st.write(f"To {exchange['role']}: {exchange['question']}")
                    with st.chat_message('assistant'):
                        st.write(exchange['answer'])
                        st.caption('Supporting metrics: '+(', '.join(exchange['supporting_metric_ids']) or 'None cited'))
                        if exchange['mode']=='Demo / offline': st.caption('Offline illustrative response, not AI-generated.')

elif page=='Shock Engine':
    st.title('Scenario Shock Engine')
    s=load_scenario_options()
    if s:
        kind=st.selectbox('Shock type',['Customer orders cancelled','Raw material inflation','Interest-rate increase'])
        mag=st.slider('Shock magnitude (%)',0,60,20 if kind=='Customer orders cancelled' else (10 if kind=='Raw material inflation' else 3))
        try:
            updated=shocked(Inputs(**s['inputs']),kind,mag)
            modified=compare(updated)
            st.subheader('Year-one comparison')
            a,b=st.columns(2)
            a.metric('Original EBITDA',f"₹{s['results']['proposal'][0]['ebitda']:.2f}L")
            b.metric('Shocked EBITDA',f"₹{modified['proposal'][0]['ebitda']:.2f}L",delta=f"{modified['proposal'][0]['ebitda']-s['results']['proposal'][0]['ebitda']:.2f}L")
            x,y=st.columns(2)
            x.metric('Original cash',f"₹{s['results']['proposal'][0]['closing_cash']:.2f}L")
            y.metric('Shocked cash',f"₹{modified['proposal'][0]['closing_cash']:.2f}L",delta=f"{modified['proposal'][0]['closing_cash']-s['results']['proposal'][0]['closing_cash']:.2f}L")
            if st.button('Save Shock Scenario & Reconvene Later',type='primary'):
                new_id=save_scenario(s['company'],f'{s["title"]} · {kind} {mag}%',asdict(updated),modified,parent_id=s['id'])
                st.session_state.scenario_id=new_id;st.session_state.meeting_id=None
                st.success(f'Shock saved as scenario #{new_id}. Open AI Boardroom to reconvene directors.')
        except Exception as e:st.error(str(e))

elif page=='Reports':
    st.title('Decision Reports')
    meetings=list_meetings()
    if not meetings:st.info('Convene an AI board meeting to create a report.');st.stop()
    ids=[m[0] for m in meetings]
    default=ids.index(st.session_state.meeting_id) if st.session_state.meeting_id in ids else 0
    mid=st.selectbox('Board meeting',ids,index=default,format_func=lambda v:f'Meeting #{v}')
    m=get_meeting(mid);s=get_scenario(m['scenario_id']);r=m['meeting']
    st.subheader(s['title']);st.write(r.get('recommendation','Incomplete meeting'))
    st.dataframe(pd.DataFrame(s['results']['proposal']).round(2),use_container_width=True,hide_index=True)
    st.subheader('Directors’ advisory votes')
    vote_rows=[{'Director':name,'Vote':vote} for name,vote in r.get('votes',{}).items()]
    if vote_rows:st.dataframe(pd.DataFrame(vote_rows),hide_index=True,use_container_width=True)
    else:st.warning('This meeting has no completed final vote.')
    st.caption('AI-generated decision support; not a statutory board resolution, audit opinion or financing approval.')
    try:
        pdf=pdf_report(s,m)
        st.download_button('Download Decision Report PDF',pdf,file_name=f'AI_Boardroom_Meeting_{mid}.pdf',mime='application/pdf',type='primary')
    except Exception as e:st.error(f'PDF generation failed: {e}')
