White Listed Tables : 
Only these Tables are used in this system

        "plot",
        "plot_action_status",
        "plot_dept_mapping",
        "plot_docs",
        "plot_ext_mstr_plan_zone",
        "plot_ext_reservation",
        "plot_fair_mkt_value",
        "plot_letout_mapping",
        "plot_merge_tbl",
        "plot_mstr_plan_zone",
        "plot_proposed_mstr_plan_zone",
        "plot_proposed_reservation",
        "plot_rmk",
        "plot_rr_land_value",
        "plot_sor_market_value",
        "plot_split_merge",
        "plot_test",
        "plot_zone_details",
        "pmemo"



to run  the code(CLI)  : cd "D:\AI-PMS\RAG\RAG_SYSTEM"
.\.venv\Scripts\python.exe scripts\test_multihop_agent.py 


 .\.venv\Scripts\python.exe -m uvicorn app.api_server:app --host 127.0.0.1 --port 8000


DrawBacks : 

the system is talking too much of time, optimization are required. 


basic rag chatbot on docs--  done 
postgres sql data integration still pending : i dont know which tables are much important so trapped.
small small refinements are to be done on the . some are done before .