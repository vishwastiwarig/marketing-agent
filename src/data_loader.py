import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Any

class DatasetLoader:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.datasets = {}
        
    def load_all_datasets(self):
        """Load all CSV files into memory"""
        csv_files = {
            'leads': 'leads.csv',
            'campaigns': 'campaigns.csv', 
            'interactions': 'interactions.csv',
            'agent_actions': 'agent_actions.csv',
            'campaign_daily': 'campaign_daily.csv',
            'conversions': 'conversions.csv',
            'memory_short_term': 'memory_short_term.csv',
            'memory_long_term': 'memory_long_term.csv',
            'memory_episodic': 'memory_episodic.csv',
            'semantic_kg_triples': 'semantic_kg_triples.csv',
            'mcp_jsonrpc_calls': 'mcp_jsonrpc_calls.csv',
            'ab_variants': 'ab_variants.csv'
        }
        
        for name, filename in csv_files.items():
            file_path = self.data_dir / filename
            if file_path.exists():
                print(f"📁 Loading {filename}...")
                self.datasets[name] = pd.read_csv(file_path)
                print(f"✅ Loaded {len(self.datasets[name])} rows from {filename}")
            else:
                print(f"⚠️  {filename} not found, using mock data")
        
        return self.datasets
    
    def get_sample_leads(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get sample leads for testing"""
        if 'leads' in self.datasets:
            sample = self.datasets['leads'].head(n)
            return sample.to_dict('records')
        return []
    
    def get_triage_patterns(self) -> Dict[str, Any]:
        """Extract triage patterns from data"""
        if 'leads' not in self.datasets:
            return {}
            
        leads_df = self.datasets['leads']
        
        # Calculate success rates by category
        patterns = {}
        for category in leads_df['triage_category'].unique():
            category_leads = leads_df[leads_df['triage_category'] == category]
            
            patterns[category] = {
                'count': len(category_leads),
                'avg_score': category_leads['lead_score'].mean(),
                'industries': category_leads['industry'].value_counts().to_dict(),
                'company_sizes': category_leads['company_size'].value_counts().to_dict()
            }
        
        return patterns
    
    def get_interaction_patterns(self) -> Dict[str, Any]:
        """Extract engagement patterns from interactions"""
        if 'interactions' not in self.datasets:
            return {}
            
        interactions_df = self.datasets['interactions']
        
        # Analyze channel effectiveness
        channel_stats = {}
        for channel in interactions_df['channel'].unique():
            channel_data = interactions_df[interactions_df['channel'] == channel]
            
            positive_outcomes = len(channel_data[channel_data['outcome'] == 'positive'])
            total_interactions = len(channel_data)
            
            channel_stats[channel] = {
                'total_interactions': total_interactions,
                'positive_rate': positive_outcomes / total_interactions if total_interactions > 0 else 0,
                'common_events': channel_data['event_type'].value_counts().head(3).to_dict()
            }
        
        return channel_stats

# Global data loader instance
data_loader = DatasetLoader()