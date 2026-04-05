from ..extensions import db


class MindMap(db.Model):
    __tablename__ = "mind_maps"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    is_shared = db.Column(db.Boolean, default=False)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    anon_token = db.Column(db.String(36), nullable=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=True)

    user = db.relationship("User", back_populates="mind_maps")
    subject = db.relationship("Subject", back_populates="mind_maps")
    nodes = db.relationship("MindMapNode", back_populates="mind_map", cascade="all, delete-orphan", lazy="dynamic")
    edges = db.relationship("MindMapEdge", back_populates="mind_map", cascade="all, delete-orphan", lazy="dynamic")

    def to_cytoscape(self) -> dict:
        """Return Cytoscape.js compatible elements dict."""
        elements = []
        for node in self.nodes:
            elements.append({
                "data": {"id": f"n{node.id}", "label": node.label, "color": node.color},
                "position": {"x": node.x, "y": node.y},
            })
        for edge in self.edges:
            elements.append({
                "data": {
                    "id": f"e{edge.id}",
                    "source": f"n{edge.source_node_id}",
                    "target": f"n{edge.target_node_id}",
                    "label": edge.label,
                },
            })
        return elements

    def __repr__(self) -> str:
        return f"<MindMap {self.title}>"


class MindMapNode(db.Model):
    __tablename__ = "mind_map_nodes"

    id = db.Column(db.Integer, primary_key=True)
    map_id = db.Column(db.Integer, db.ForeignKey("mind_maps.id"), nullable=False)
    label = db.Column(db.String(200), nullable=False)
    x = db.Column(db.Float, default=0.0)
    y = db.Column(db.Float, default=0.0)
    color = db.Column(db.String(7), default="#7c3aed")

    mind_map = db.relationship("MindMap", back_populates="nodes")

    def __repr__(self) -> str:
        return f"<MindMapNode {self.label}>"


class MindMapEdge(db.Model):
    __tablename__ = "mind_map_edges"

    id = db.Column(db.Integer, primary_key=True)
    map_id = db.Column(db.Integer, db.ForeignKey("mind_maps.id"), nullable=False)
    source_node_id = db.Column(db.Integer, db.ForeignKey("mind_map_nodes.id"), nullable=False)
    target_node_id = db.Column(db.Integer, db.ForeignKey("mind_map_nodes.id"), nullable=False)
    label = db.Column(db.String(200), default="")

    mind_map = db.relationship("MindMap", back_populates="edges")

    def __repr__(self) -> str:
        return f"<MindMapEdge {self.source_node_id} -> {self.target_node_id}>"
