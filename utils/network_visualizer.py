"""
Network Visualization Module

Create interactive visualizations of your LinkedIn network including:
- Connection graphs with companies and engagement levels
- Interactive HTML network maps
- Network analytics and insights
"""

import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

import networkx as nx
from pyvis.network import Network
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

from database.models import Connection
from database.session import get_session

logger = logging.getLogger(__name__)


class NetworkVisualizer:
    """Visualize LinkedIn network connections as interactive graphs"""

    def __init__(self):
        self.session = get_session()
        self.graph = None

    def build_network_graph(
        self,
        min_quality_score: float = 0.0,
        include_inactive: bool = False,
        max_connections: Optional[int] = None
    ) -> nx.Graph:
        """
        Build a NetworkX graph from connection data.

        Args:
            min_quality_score: Minimum quality score to include
            include_inactive: Whether to include inactive connections
            max_connections: Maximum number of connections to include

        Returns:
            NetworkX Graph object
        """
        logger.info("Building network graph...")

        # Query connections
        query = self.session.query(Connection).filter(
            Connection.quality_score >= min_quality_score
        )

        if not include_inactive:
            query = query.filter(Connection.is_active == True)

        if max_connections:
            query = query.limit(max_connections)

        connections = query.all()

        logger.info(f"Processing {len(connections)} connections")

        # Create graph
        G = nx.Graph()

        # Add "You" as the center node
        G.add_node(
            "You",
            node_type="self",
            title="You",
            company="",
            quality=10.0,
            engagement="high",
            size=50
        )

        # Add connections as nodes
        for conn in connections:
            node_id = f"conn_{conn.id}"

            # Determine engagement level
            if conn.engagement_level:
                engagement = conn.engagement_level
            elif conn.quality_score >= 7:
                engagement = "high"
            elif conn.quality_score >= 4:
                engagement = "medium"
            else:
                engagement = "low"

            G.add_node(
                node_id,
                node_type="connection",
                title=conn.title or "Unknown",
                name=conn.name,
                company=conn.company or "Unknown",
                quality=conn.quality_score,
                engagement=engagement,
                is_target=conn.is_target_audience,
                messages_sent=conn.messages_sent,
                messages_received=conn.messages_received,
                size=20 + (conn.quality_score * 2)  # Size based on quality
            )

            # Add edge from you to this connection
            G.add_edge("You", node_id, weight=conn.quality_score)

        # Group connections by company to create company clusters
        company_groups = {}
        for node, data in G.nodes(data=True):
            if data.get('node_type') == 'connection':
                company = data.get('company', 'Unknown')
                if company not in company_groups:
                    company_groups[company] = []
                company_groups[company].append(node)

        # Add edges between connections from same company
        for company, nodes in company_groups.items():
            if len(nodes) > 1:
                # Create connections between people from same company
                for i, node1 in enumerate(nodes):
                    for node2 in nodes[i+1:]:
                        G.add_edge(node1, node2, weight=0.3, edge_type="same_company")

        self.graph = G
        logger.info(f"Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        return G

    def create_interactive_visualization(
        self,
        output_file: str = "network_graph.html",
        height: str = "750px",
        width: str = "100%",
        physics: bool = True
    ) -> str:
        """
        Create an interactive HTML network visualization using PyVis.

        Args:
            output_file: Output HTML filename
            height: Graph height
            width: Graph width
            physics: Enable physics simulation

        Returns:
            Path to generated HTML file
        """
        if not self.graph:
            self.build_network_graph()

        logger.info(f"Creating interactive visualization: {output_file}")

        # Create PyVis network
        net = Network(
            height=height,
            width=width,
            bgcolor="#222222",
            font_color="white",
            notebook=False
        )

        # Configure physics
        if physics:
            net.barnes_hut(
                gravity=-8000,
                central_gravity=0.3,
                spring_length=200,
                spring_strength=0.001,
                damping=0.09
            )
        else:
            net.toggle_physics(False)

        # Color mapping for engagement levels
        color_map = {
            "self": "#FFD700",      # Gold for you
            "high": "#00FF00",      # Green for high engagement
            "medium": "#FFA500",    # Orange for medium
            "low": "#FF6B6B",       # Red for low
            "none": "#808080"       # Gray for no engagement
        }

        # Add nodes to PyVis
        for node, data in self.graph.nodes(data=True):
            node_type = data.get('node_type', 'connection')

            if node_type == 'self':
                color = color_map['self']
                size = 50
                title = "You (Center)"
                label = "YOU"
            else:
                engagement = data.get('engagement', 'none')
                color = color_map.get(engagement, color_map['none'])
                size = data.get('size', 20)
                quality = data.get('quality', 0)
                is_target = data.get('is_target', False)

                name = data.get('name', 'Unknown')
                title_text = data.get('title', 'Unknown')
                company = data.get('company', 'Unknown')

                # Create hover tooltip
                title = f"""
                <b>{name}</b><br>
                {title_text}<br>
                {company}<br>
                <br>
                Quality Score: {quality:.1f}/10<br>
                Engagement: {engagement.title()}<br>
                {'⭐ Target Audience' if is_target else ''}
                """

                label = name.split()[0] if name else "?"  # First name only

                # Highlight target audience
                if is_target:
                    color = "#9B59B6"  # Purple for target audience

            net.add_node(
                node,
                label=label,
                title=title,
                color=color,
                size=size
            )

        # Add edges to PyVis
        for source, target, data in self.graph.edges(data=True):
            weight = data.get('weight', 1.0)
            edge_type = data.get('edge_type', 'direct')

            if edge_type == "same_company":
                # Thin gray lines for same-company connections
                net.add_edge(source, target, color="#444444", width=0.5)
            else:
                # Thicker lines for your direct connections, width based on quality
                width = weight / 2  # Scale down the weight
                net.add_edge(source, target, width=width)

        # Set options
        net.set_options("""
        {
          "nodes": {
            "borderWidth": 2,
            "borderWidthSelected": 4,
            "font": {
              "size": 14,
              "face": "arial"
            }
          },
          "edges": {
            "color": {
              "inherit": false
            },
            "smooth": {
              "type": "continuous"
            }
          },
          "interaction": {
            "hover": true,
            "tooltipDelay": 100,
            "zoomView": true,
            "dragView": true
          }
        }
        """)

        # Save to file
        net.save_graph(output_file)

        logger.info(f"Visualization saved to: {output_file}")
        return output_file

    def get_network_stats(self) -> Dict:
        """
        Calculate network statistics.

        Returns:
            Dictionary with network stats
        """
        if not self.graph:
            self.build_network_graph()

        # Get all connection nodes (exclude "You")
        connection_nodes = [n for n, d in self.graph.nodes(data=True) if d.get('node_type') == 'connection']

        # Company distribution
        companies = [self.graph.nodes[n].get('company', 'Unknown') for n in connection_nodes]
        company_counts = Counter(companies).most_common(10)

        # Engagement distribution
        engagements = [self.graph.nodes[n].get('engagement', 'none') for n in connection_nodes]
        engagement_counts = Counter(engagements)

        # Quality score distribution
        qualities = [self.graph.nodes[n].get('quality', 0) for n in connection_nodes]
        avg_quality = sum(qualities) / len(qualities) if qualities else 0

        # Target audience count
        target_count = sum(1 for n in connection_nodes if self.graph.nodes[n].get('is_target', False))

        # Network density and clustering
        density = nx.density(self.graph)

        return {
            'total_connections': len(connection_nodes),
            'total_companies': len(set(companies)),
            'top_companies': company_counts,
            'engagement_distribution': dict(engagement_counts),
            'avg_quality_score': round(avg_quality, 2),
            'target_audience_count': target_count,
            'network_density': round(density, 4),
            'avg_connections_per_company': round(len(connection_nodes) / len(set(companies)), 2) if companies else 0
        }

    def identify_clusters(self) -> List[List[str]]:
        """
        Identify clusters/communities in the network.

        Returns:
            List of clusters (each cluster is a list of node IDs)
        """
        if not self.graph:
            self.build_network_graph()

        # Use community detection algorithm
        from networkx.algorithms import community

        # Get communities
        communities = community.greedy_modularity_communities(self.graph)

        clusters = []
        for i, comm in enumerate(communities):
            cluster_nodes = list(comm)
            # Get companies in this cluster
            companies = [
                self.graph.nodes[n].get('company', 'Unknown')
                for n in cluster_nodes
                if self.graph.nodes[n].get('node_type') == 'connection'
            ]
            company_counts = Counter(companies)

            clusters.append({
                'cluster_id': i + 1,
                'size': len(cluster_nodes),
                'nodes': cluster_nodes,
                'dominant_companies': company_counts.most_common(3)
            })

        return clusters

    def get_key_connectors(self, top_n: int = 10) -> List[Dict]:
        """
        Identify key connectors in your network (highest betweenness centrality).

        Args:
            top_n: Number of top connectors to return

        Returns:
            List of key connector nodes with their metrics
        """
        if not self.graph:
            self.build_network_graph()

        # Calculate betweenness centrality
        betweenness = nx.betweenness_centrality(self.graph)

        # Get connection nodes only
        connection_centrality = {
            node: score
            for node, score in betweenness.items()
            if self.graph.nodes[node].get('node_type') == 'connection'
        }

        # Sort by centrality
        sorted_connectors = sorted(
            connection_centrality.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]

        # Build result
        result = []
        for node, centrality in sorted_connectors:
            data = self.graph.nodes[node]
            result.append({
                'name': data.get('name', 'Unknown'),
                'title': data.get('title', 'Unknown'),
                'company': data.get('company', 'Unknown'),
                'quality_score': data.get('quality', 0),
                'centrality': round(centrality, 4),
                'engagement': data.get('engagement', 'none')
            })

        return result
