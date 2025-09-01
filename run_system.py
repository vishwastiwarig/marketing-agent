import asyncio
from src.handoff_protocols import create_marketing_system
from src.data_loader import data_loader

async def main():
    print("\n🚀 Starting Marketing System with Real Data...")

    
    print("\n📊 Loading Dataset...")
    datasets = data_loader.load_all_datasets()

   
    system = await create_marketing_system()

   
    print("\n🧠 Initializing memory systems with historical data...")
    await system.memory_manager.initialize_all_memory_systems()

    
    sample_leads = data_loader.get_sample_leads(3)

    print(f"\n🧪 Testing with {len(sample_leads)} real leads...")

    for lead_data in sample_leads:
        print(f"\n[NARRATOR] Main: Processing lead {lead_data['lead_id']} through the system...")
        result = await system.process_lead(lead_data)
        if result['success']:
            print(f"[NARRATOR] Main: Lead {lead_data['lead_id']} triaged as {result['triage_result']['triage_category']}")
            print(f"[NARRATOR] Main: Engagement plan: {result['engagement_result']['engagement_plan']}")
        else:
            print(f"[NARRATOR] Main: Lead {lead_data['lead_id']} processing failed: {result.get('error')}")

    await system.stop_system()
    print("\n🏁 Complete!")

if __name__ == "__main__":
    asyncio.run(main())
