from io import BytesIO
from pathlib import Path
from datetime import date
import html
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from utils.database import read_table, add_record, delete_record

STATIONS = {
 "CMN":(33.3675,-7.5898,"Casablanca"), "RAK":(31.6069,-8.0363,"Marrakech"),
 "TNG":(35.7269,-5.9169,"Tanger"), "AGA":(30.3250,-9.4131,"Agadir"),
 "FEZ":(33.9273,-4.9779,"Fès"), "OUD":(34.7872,-1.9239,"Oujda")
}

def _map(df):
    counts=df.groupby('station',as_index=False).agg(orders=('work_order_id','nunique'), aircraft=('aircraft_reg','nunique'))
    counts=counts[counts.station.isin(STATIONS)].copy()
    if counts.empty:
        st.info('Aucune escale reconnue dans les filtres.')
        return
    counts['lat']=counts.station.map(lambda x:STATIONS[x][0])
    counts['lon']=counts.station.map(lambda x:STATIONS[x][1])
    counts['airport']=counts.station.map(lambda x:STATIONS[x][2])
    total_orders=int(counts.orders.sum()); total_aircraft=int(df.aircraft_reg.nunique())
    total_stations=len(counts); total_downtime=float(df[df.station.isin(STATIONS)].aircraft_downtime_h.sum())
    st.markdown('''<div class="network-hero"><div><div class="network-kicker">AERONEX / MAINTENANCE NETWORK</div><div class="network-title">Carte du réseau de maintenance</div><div class="network-subtitle">Centres opérationnels · connectivité des escales · activité issue des données</div></div><div class="network-orbit">✈</div></div>''',unsafe_allow_html=True)
    m1,m2,m3,m4=st.columns(4)
    m1.metric('CENTRES IDENTIFIÉS',f'{total_stations:02d}')
    m2.metric('ORDRES DE TRAVAIL',f'{total_orders:,}'.replace(',',' '))
    m3.metric('AVIONS CONCERNÉS',f'{total_aircraft:02d}')
    m4.metric('IMMOBILISATION',f'{total_downtime:,.0f} h')
    hub='CMN'; fig=go.Figure()
    for code in counts.station:
        if code == hub: continue
        a=STATIONS[hub]; b=STATIONS[code]
        fig.add_trace(go.Scattergeo(lon=[a[1],b[1]],lat=[a[0],b[0]],mode='lines',line=dict(width=2.5,color='rgba(35,177,255,.78)'),hoverinfo='skip',showlegend=False))
    max_orders=max(float(counts.orders.max()),1.0)
    fig.add_trace(go.Scattergeo(lon=counts.lon,lat=counts.lat,mode='markers',marker=dict(size=counts.orders.map(lambda x:22+24*float(x)/max_orders),color='rgba(0,150,255,.12)',line=dict(width=0)),hoverinfo='skip',showlegend=False))
    fig.add_trace(go.Scattergeo(lon=counts.lon,lat=counts.lat,mode='markers+text',text=counts.airport,textposition='top center',customdata=counts[['airport','station','orders','aircraft']].to_numpy(),marker=dict(size=counts.orders.map(lambda x:10+12*float(x)/max_orders),color=counts.orders,colorscale=[[0,'#25c6ff'],[.55,'#287cff'],[1,'#a56cff']],line=dict(width=2,color='#e7f8ff'),showscale=False),textfont=dict(color='#f1f8ff',size=12,family='Arial Black'),hovertemplate='<b>%{customdata[0]}</b><br>Code: %{customdata[1]}<br>Ordres: %{customdata[2]}<br>Avions: %{customdata[3]}<extra></extra>',showlegend=False))
    # Center and crop the geographic view around Morocco instead of using the
    # Africa-wide default extent (which made the country look stretched/clipped).
    fig.update_geos(
        projection_type='mercator', projection_scale=4.2,
        center=dict(lat=32.1, lon=-6.4),
        lataxis_range=[27.0, 36.8], lonaxis_range=[-14.2, -0.7],
        showland=True, landcolor='#102d57',
        showocean=True, oceancolor='#03132e',
        showlakes=True, lakecolor='#03132e',
        showcountries=True, countrycolor='rgba(80,160,255,.42)',
        showcoastlines=True, coastlinecolor='rgba(45,175,255,.72)',
        showframe=False, bgcolor='rgba(0,0,0,0)'
    )
    fig.update_layout(
        height=520, autosize=True,
        margin=dict(l=8,r=8,t=34,b=8),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#eaf4ff',family='Arial'),
        title=dict(text='MOROCCO · MAINTENANCE OPERATIONS NETWORK',
                   font=dict(size=12,color='#75cfff'),x=.02,y=.99),
        geo=dict(bgcolor='rgba(0,0,0,0)')
    )
    left,right=st.columns([.9,2.1],gap='large')
    with left:
        st.markdown('<div class="network-panel-title">✧ &nbsp; CENTRES DU RÉSEAU</div>',unsafe_allow_html=True)
        for _,row in counts.sort_values('orders',ascending=False).iterrows():
            code=str(row.station); airport=str(row.airport); is_hub=code=='CMN'
            icon='✈' if is_hub else '⌖'; status='HUB' if is_hub else 'ACTIF'
            card=(f'<div class="network-station"><div class="network-station-icon">{icon}</div><div class="network-station-copy"><strong>{html.escape(airport)}</strong><small>{html.escape(code)} · {int(row.aircraft)} avion(s) · {int(row.orders)} ordres</small></div><span class="network-status">{status}</span></div>')
            st.markdown(card,unsafe_allow_html=True)
        st.markdown('<div class="network-note"><span>●</span> Données opérationnelles filtrées</div>',unsafe_allow_html=True)
    with right:
        st.plotly_chart(fig,use_container_width=True,config={'displayModeBar':False})
    st.caption('Positions fixes des aéroports connues dans le jeu de données. Cette carte représente le réseau de maintenance, ni GPS ni suivi de vol en temps réel.')

def render(page, df, filtered, lang="fr"):
    rtl = lang == "ar"
    if rtl:
        st.markdown("<style>.main .block-container{direction:rtl;text-align:right}.stSelectbox,.stTextInput,.stNumberInput,.stTextArea{direction:rtl}</style>",unsafe_allow_html=True)
    if page == "Carte mondiale":
        st.subheader("Carte du réseau de maintenance" if lang!="en" else "Maintenance network map")
        _map(filtered)
        st.dataframe(filtered.groupby("station",as_index=False).agg(
            Ordres=("work_order_id","nunique"),Avions=("aircraft_reg","nunique"),
            Immobilisation_h=("aircraft_downtime_h","sum")),use_container_width=True,hide_index=True)
        return True

    if page == "Fiches avions interactives":
        st.subheader("Aircraft Profile · Dossier technique du modèle")
        st.caption("Profil analytique construit à partir des ordres de travail du CSV. Il ne remplace pas les dossiers techniques approuvés ni les échéances réglementaires.")
        models=sorted(filtered.aircraft_type.dropna().astype(str).unique().tolist())
        if not models:
            st.info("Aucun modèle ne correspond aux filtres actifs."); return True
        preferred=st.session_state.get("profile_model")
        model_index=models.index(preferred) if preferred in models else 0
        model=st.selectbox("Aircraft model",models,index=model_index,key="aircraft_profile_model")
        model_df=filtered[filtered.aircraft_type.astype(str).eq(model)].copy()
        model_df=model_df.sort_values("open_datetime",ascending=False)
        if model_df.empty:
            st.info("Aucune donnée disponible pour ce modèle."); return True

        model_photos={
            "B737-800":"https://commons.wikimedia.org/wiki/Special:FilePath/B737-800.jpg?width=1400",
            "ATR 72-600":"https://commons.wikimedia.org/wiki/Special:FilePath/An_ATR_72-600.jpg?width=1400",
            "B787-8":"https://commons.wikimedia.org/wiki/Special:FilePath/Boeing_787-8_first_flight_photographers.jpg?width=1400",
            "B787-9":"https://commons.wikimedia.org/wiki/Special:FilePath/ANA_Boeing_787-9.jpg?width=1400",
            "E190":"https://commons.wikimedia.org/wiki/Special:FilePath/AERONAVE_EMBRAER_E-190.jpg?width=1400",
        }
        maker={"B737-800":"Boeing","ATR 72-600":"ATR","B787-8":"Boeing","B787-9":"Boeing","E190":"Embraer"}.get(model,"Constructeur non précisé")
        if model in model_photos:
            st.image(model_photos[model],use_container_width=True)
        st.markdown(f"## {model}  ·  {maker}")
        aircraft_count=model_df.aircraft_reg.nunique()
        order_count=model_df.work_order_id.nunique()
        total_cost=float(model_df.total_cost_usd.sum())
        total_dt=float(model_df.aircraft_downtime_h.sum())
        c1,c2,c3,c4,c5=st.columns(5)
        c1.metric("Aircraft",f"{aircraft_count:,}")
        c2.metric("Work orders",f"{order_count:,}")
        c3.metric("Maintenance cost",f"${total_cost:,.0f}")
        c4.metric("Downtime",f"{total_dt:,.1f} h")
        c5.metric("Avg. age",f"{model_df.drop_duplicates('aircraft_reg').aircraft_age_years.mean():.1f} yrs")

        st.markdown("### Technical & operational profile")
        reg_summary=model_df.groupby("aircraft_reg",as_index=False).agg(
            orders=("work_order_id","nunique"),cost=("total_cost_usd","sum"),
            downtime=("aircraft_downtime_h","sum"),age=("aircraft_age_years","mean"),
            flight_hours=("flight_hours_total","max"),cycles=("flight_cycles_total","max"),
            last_activity=("open_datetime","max"))
        reg_summary["cost_per_order"]=reg_summary.cost/reg_summary.orders.clip(lower=1)
        st.dataframe(reg_summary.sort_values("orders",ascending=False).rename(columns={
            "aircraft_reg":"Registration","orders":"Work orders","cost":"Total cost USD",
            "downtime":"Downtime h","age":"Age years","flight_hours":"Flight hours",
            "cycles":"Flight cycles","last_activity":"Last maintenance","cost_per_order":"Cost / order USD"
        }).round(2),use_container_width=True,hide_index=True)

        left,right=st.columns(2)
        with left:
            costs=model_df[["parts_cost_usd","labor_cost_usd"]].sum().rename(
                {"parts_cost_usd":"Parts","labor_cost_usd":"Labor"}).reset_index()
            costs.columns=["Cost category","USD"]
            fig=px.pie(costs,names="Cost category",values="USD",hole=.58,title="Cost composition")
            st.plotly_chart(fig,use_container_width=True)
        with right:
            ata=model_df.groupby("ata_system",as_index=False).agg(
                orders=("work_order_id","nunique"),cost=("total_cost_usd","sum")).nlargest(10,"orders")
            fig=px.bar(ata.sort_values("orders"),x="orders",y="ata_system",orientation="h",
                       title="Most frequent ATA systems",labels={"orders":"Work orders","ata_system":"ATA system"})
            st.plotly_chart(fig,use_container_width=True)

        monthly=model_df.assign(month=model_df.open_datetime.dt.to_period("M").astype(str)).groupby(
            "month",as_index=False).agg(orders=("work_order_id","nunique"),
                                         cost=("total_cost_usd","sum"),downtime=("aircraft_downtime_h","sum"))
        fig=px.line(monthly,x="month",y=["orders","downtime"],markers=True,
                    title="Maintenance activity & downtime trend",
                    labels={"value":"Observed value","month":"Month","variable":"Metric"})
        st.plotly_chart(fig,use_container_width=True)

        st.markdown("### Aircraft detail")
        regs=sorted(model_df.aircraft_reg.dropna().astype(str).unique().tolist())
        reg=st.selectbox("Registration",regs,key="profile_registration")
        d=model_df[model_df.aircraft_reg.astype(str).eq(reg)].sort_values("open_datetime",ascending=False)
        latest=d.iloc[0]
        x1,x2,x3,x4=st.columns(4)
        x1.metric("Age",f"{latest.aircraft_age_years:.0f} years")
        x2.metric("Flight hours",f"{latest.flight_hours_total:,.0f}")
        x3.metric("Flight cycles",f"{latest.flight_cycles_total:,.0f}")
        x4.metric("Orders",f"{d.work_order_id.nunique():,}")
        st.markdown("#### Maintenance history")
        st.dataframe(d[["work_order_id","open_datetime","close_datetime","station","maintenance_type",
                        "ata_system","finding","priority","status","parts_cost_usd","labor_cost_usd",
                        "total_cost_usd","aircraft_downtime_h","repeat_defect"]],
                     use_container_width=True,hide_index=True)
        st.caption("Les heures de vol, cycles et âge sont repris des valeurs source les plus récentes observées. Les données ne contiennent pas de preuve d’état de navigabilité ni de programme de maintenance approuvé.")
        return True

    if page == "Planning de maintenance":
        st.subheader("Planning de maintenance — données persistantes")
        st.caption("Remplis les champs clairs ci-dessous, puis clique sur « Ajouter au planning » pour enregistrer l’intervention.")
        with st.form("plan_add",clear_on_submit=True):
            a,b=st.columns(2)
            reg=a.selectbox("Avion",sorted(df.aircraft_reg.unique()))
            task=b.text_input("Intervention / inspection",placeholder="Ex. Inspection visuelle")
            c,d=st.columns(2)
            due=c.date_input("Échéance",value=date.today())
            priority=d.selectbox("Priorité",["Low","Medium","High","AOG"])
            assigned=st.text_input("Responsable")
            notes=st.text_area("Notes")
            submit=st.form_submit_button("Ajouter au planning",use_container_width=True)
        if submit:
            if not task.strip(): st.error("Décris l’intervention avant l’enregistrement.")
            else:
                add_record("maintenance_plan",{"aircraft_reg":reg,"task":task.strip(),"due_date":due.isoformat(),"priority":priority,"status":"Planned","assigned_to":assigned,"notes":notes})
                st.success("Intervention enregistrée dans la base locale."); st.rerun()
        plan=read_table("maintenance_plan")
        if not plan.empty:
            plan["due_date"]=pd.to_datetime(plan.due_date)
            st.dataframe(plan,use_container_width=True,hide_index=True)
            st.markdown("#### Calendrier")
            cal=plan.copy(); cal["Jour"]=cal.due_date.dt.strftime("%d/%m/%Y")
            st.dataframe(cal[["Jour","aircraft_reg","task","priority","status","assigned_to"]].sort_values("Jour"),use_container_width=True,hide_index=True)
            ids=plan.id.tolist()
            chosen=st.selectbox("Supprimer une entrée",ids,format_func=lambda x:f"#{x} · {plan.loc[plan.id.eq(x),'task'].iloc[0]}")
            if st.button("Supprimer l’entrée sélectionnée"): delete_record("maintenance_plan",chosen); st.rerun()
        else: st.info("Le planning est vide. Ajoute une intervention pour commencer.")
        return True

    if page == "Stocks de pièces":
        st.subheader("Gestion des stocks — SQLite persistant")
        with st.form("part_add",clear_on_submit=True):
            c=st.columns(3)
            pn=c[0].text_input("Référence pièce"); desc=c[1].text_input("Description"); loc=c[2].text_input("Magasin / escale")
            c=st.columns(3)
            qty=c[0].number_input("Quantité",min_value=0,step=1); minimum=c[1].number_input("Seuil minimum",min_value=0,step=1); cost=c[2].number_input("Coût unitaire USD",min_value=0.0,step=10.0)
            submit=st.form_submit_button("Ajouter la pièce")
        if submit:
            try:
                if not pn.strip() or not desc.strip(): st.error("Référence et description obligatoires.")
                else: add_record("parts_inventory",{"part_number":pn.strip(),"description":desc.strip(),"quantity":int(qty),"min_quantity":int(minimum),"location":loc,"unit_cost":float(cost)}); st.success("Pièce enregistrée."); st.rerun()
            except Exception as e: st.error(f"Enregistrement impossible : {e}")
        parts=read_table("parts_inventory")
        if not parts.empty:
            parts["Alerte"]=parts.quantity<=parts.min_quantity
            a,b=st.columns(2); a.metric("Références suivies",len(parts)); b.metric("Sous le seuil",int(parts.Alerte.sum()))
            st.dataframe(parts,use_container_width=True,hide_index=True)
            low=parts[parts.Alerte]
            if not low.empty: st.warning("Réapprovisionnement à étudier : "+", ".join(low.part_number.astype(str).tolist()))
            chosen=st.selectbox("Référence à supprimer",parts.id.tolist(),format_func=lambda x:parts.loc[parts.id.eq(x),"part_number"].iloc[0])
            if st.button("Supprimer cette référence"): delete_record("parts_inventory",chosen); st.rerun()
        else: st.info("Aucune pièce enregistrée. Le stock n’est pas inventé à partir des coûts historiques.")
        return True

    if page == "Gestion des techniciens":
        st.subheader("Répertoire des techniciens")
        with st.form("tech_add",clear_on_submit=True):
            a,b=st.columns(2); name=a.text_input("Nom complet"); specialty=b.text_input("Spécialité / habilitation")
            c,d=st.columns(2); station=c.selectbox("Base",sorted(df.station.unique())); email=d.text_input("E-mail")
            availability=st.selectbox("Disponibilité déclarée",["Disponible","Affecté","Absent"])
            submit=st.form_submit_button("Ajouter le technicien")
        if submit:
            if not name.strip(): st.error("Le nom est obligatoire.")
            else: add_record("technicians",{"full_name":name.strip(),"specialty":specialty,"station":station,"email":email,"availability":availability}); st.success("Technicien ajouté."); st.rerun()
        tech=read_table("technicians")
        st.metric("Techniciens répertoriés",len(tech))
        if not tech.empty:
            st.dataframe(tech,use_container_width=True,hide_index=True)
            chosen=st.selectbox("Technicien à supprimer",tech.id.tolist(),format_func=lambda x:tech.loc[tech.id.eq(x),"full_name"].iloc[0])
            if st.button("Supprimer ce technicien"): delete_record("technicians",chosen); st.rerun()
        st.caption("Les compétences et disponibilités sont des données saisies par l’administrateur, pas des habilitations vérifiées.")
        return True

    if page == "AERONEX AI":
        st.subheader("AERONEX AI · Assistant analytique explicable")
        st.warning("Aide à la décision uniquement. Aucun diagnostic, aucune décision de navigabilité et aucune consigne de remise en service.")
        top=filtered.ata_system.value_counts()
        rep=filtered[filtered.repeat_defect.astype(str).str.lower().eq("yes")]
        aog=filtered[(filtered.maintenance_type.eq("AOG"))|(filtered.priority.eq("AOG"))]
        costs=filtered.groupby("aircraft_type").total_cost_usd.sum().sort_values(ascending=False)
        st.markdown("#### Signaux calculés depuis le filtre actif")
        if len(top): st.info(f"Système ATA le plus fréquent : **{top.index[0]}** ({int(top.iloc[0])} ordres).")
        if len(rep): st.warning(f"{len(rep)} ligne(s) portent le marqueur repeat_defect = Yes. Examiner les findings et la chronologie avec l’ingénierie.")
        if len(aog): st.error(f"{aog.work_order_id.nunique()} ordre(s) associés à AOG dans le jeu filtré.")
        if len(costs): st.info(f"Type présentant le coût cumulé observé le plus élevé : **{costs.index[0]}** ({costs.iloc[0]:,.0f} USD).")
        st.markdown("#### Explorer les défauts répétitifs")
        if not rep.empty:
            st.dataframe(rep[["aircraft_reg","aircraft_type","ata_system","finding","open_datetime","work_order_id"]].head(100),use_container_width=True,hide_index=True)
        st.caption("Ce module est une analyse descriptive déterministe ; il n’entraîne pas de modèle prédictif faute de labels, capteurs et validation suffisants.")
        return True

    if page == "Notifications intelligentes":
        st.subheader("Centre de notifications")
        alerts=[]
        for _,r in filtered.iterrows():
            if r.maintenance_type=="AOG" or r.priority=="AOG": alerts.append(("Critique","AOG",r))
            elif str(r.status).lower()=="open" and str(r.priority).lower()=="high": alerts.append(("Élevée","Ordre High ouvert",r))
            elif str(r.repeat_defect).lower()=="yes": alerts.append(("À surveiller","Défaut répétitif",r))
            elif str(r.mel_deferred).lower()=="yes": alerts.append(("À surveiller","MEL différé",r))
        st.metric("Signaux détectés",len(alerts))
        if alerts:
            for severity,label,r in alerts[:100]:
                st.markdown(f"**{severity} · {label}** — {r.aircraft_reg} / {r.work_order_id} · {r.station} · {r.ata_system} · {r.finding}")
        else: st.success("Aucun signal de cette catégorie dans le filtre actif.")
        st.caption("Alertes recalculées à partir du CSV à chaque chargement ; elles ne sont pas des notifications push et ne remplacent pas la surveillance opérationnelle.")
        return True

    if page == "Rapports PDF professionnels":
        st.subheader("Rapport PDF professionnel")
        st.caption("Synthèse descriptive des données filtrées, avec date de génération.")
        if st.button("Générer le rapport PDF"):
            try:
                from reportlab.lib import colors
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
                buf=BytesIO(); doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=38,leftMargin=38,topMargin=38,bottomMargin=38)
                styles=getSampleStyleSheet(); story=[Paragraph("AERONEX — Rapport de maintenance",styles["Title"]),Spacer(1,10)]
                story.append(Paragraph(f"Généré le {date.today().isoformat()} · {len(filtered)} lignes filtrées",styles["Normal"]))
                story.append(Spacer(1,14))
                summary=[["Indicateur","Valeur"],["Ordres distincts",str(filtered.work_order_id.nunique())],["Avions",str(filtered.aircraft_reg.nunique())],["Coût total USD",f"{filtered.total_cost_usd.sum():,.2f}"],["Immobilisation (h)",f"{filtered.aircraft_downtime_h.sum():,.1f}"],["AOG",str(((filtered.maintenance_type=="AOG")|(filtered.priority=="AOG")).sum())]]
                t=Table(summary,colWidths=[250,220]); t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#12314d")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.4,colors.lightgrey),("PADDING",(0,0),(-1,-1),7)])); story.append(t)
                story += [Spacer(1,18),Paragraph("Systèmes ATA les plus représentés",styles["Heading2"])]
                ata=filtered.ata_system.value_counts().head(10)
                rows=[["Système","Ordres"]]+[[str(k),str(v)] for k,v in ata.items()]
                t=Table(rows,colWidths=[350,120]); t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#d9eaf5")),("GRID",(0,0),(-1,-1),.4,colors.lightgrey),("PADDING",(0,0),(-1,-1),6)])); story.append(t)
                story.append(Spacer(1,14)); story.append(Paragraph("Document analytique. Ne constitue pas un dossier de navigabilité ni une approbation technique.",styles["Italic"]))
                doc.build(story); st.download_button("Télécharger AERONEX_Report.pdf",buf.getvalue(),"AERONEX_Report.pdf","application/pdf")
            except ImportError: st.error("Installe reportlab avec pip install -r requirements.txt.")
        return True
    return False
