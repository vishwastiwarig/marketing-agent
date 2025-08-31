import asyncio
from src.handoff_protocols import create_marketing_system
from src.data_loader import data_loader

async def main():
    print("\n🚀 Starting Marketing System with Real Data...")

    # 1. Load your actual dataset
    print("\n📊 Loading Dataset...")
    datasets = data_loader.load_all_datasets()

    # 2. Create system
    system = await create_marketing_system()

    # 👇 ADD THIS: Initialize memory with historical data
    print("\n🧠 Initializing memory systems with historical data...")
    await system.memory_manager.initialize_all_memory_systems()

    # 3. Test with real leads
    sample_leads = data_loader.get_sample_leads(3)

    print(f"\n🧪 Testing with {len(sample_leads)} real leads...")

    for lead_data in sample_leads:
        result = await system.process_lead(lead_data)
        if result['success']:
            print(f"✅ {lead_data['lead_id']}: {result['triage_result']['triage_category']}")

    await system.stop_system()
    print("\n🏁 Complete!")

if __name__ == "__main__":
    asyncio.run(main())