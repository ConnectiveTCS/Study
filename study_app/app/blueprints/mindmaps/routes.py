from flask import render_template, request, jsonify, redirect, url_for, g, abort
from flask_login import current_user
from . import mindmaps_bp
from app.extensions import db
from app.models.mindmap import MindMap, MindMapNode, MindMapEdge
from app.models.subject import Subject


def _owner_filter(query):
    if current_user.is_authenticated:
        return query.filter_by(user_id=current_user.id)
    return query.filter_by(anon_token=g.anon_token)


def _owner_kwargs():
    if current_user.is_authenticated:
        return {'user_id': current_user.id}
    return {'anon_token': g.anon_token}


def _can_access(obj):
    if current_user.is_authenticated:
        return obj.user_id == current_user.id
    return obj.anon_token == g.anon_token


@mindmaps_bp.route('/')
def list_maps():
    maps = _owner_filter(MindMap.query).order_by(MindMap.id.desc()).all()
    subjects = []
    if current_user.is_authenticated:
        subjects = Subject.query.filter_by(user_id=current_user.id).all()
    return render_template('mindmaps/list.html', maps=maps, subjects=subjects)


@mindmaps_bp.route('/new', methods=['POST'])
def new_map():
    title = (request.form.get('title') or '').strip()[:200]
    if not title:
        return redirect(url_for('mindmaps.list_maps'))
    m = MindMap(
        title=title,
        subject_id=request.form.get('subject_id') or None,
        **_owner_kwargs()
    )
    db.session.add(m)
    db.session.flush()
    # Create root node
    root = MindMapNode(map_id=m.id, label=title, x=400, y=300, color='#6366f1')
    db.session.add(root)
    db.session.commit()
    return redirect(url_for('mindmaps.editor', map_id=m.id))


@mindmaps_bp.route('/<int:map_id>')
def editor(map_id):
    m = MindMap.query.get_or_404(map_id)
    if not _can_access(m):
        abort(403)
    elements = m.to_cytoscape()
    return render_template('mindmaps/editor.html', map=m, elements_json=elements)


# --- Node/Edge REST API ---

@mindmaps_bp.route('/<int:map_id>/nodes', methods=['POST'])
def add_node(map_id):
    m = MindMap.query.get_or_404(map_id)
    if not _can_access(m):
        return jsonify({'ok': False}), 403
    data = request.get_json(silent=True) or {}
    label = (data.get('label') or 'New node')[:200]
    node = MindMapNode(
        map_id=map_id,
        label=label,
        x=float(data.get('x', 400)),
        y=float(data.get('y', 300)),
        color=data.get('color', '#7c3aed') or '#7c3aed'
    )
    db.session.add(node)
    db.session.commit()
    return jsonify({'ok': True, 'id': node.id, 'cy_id': f'n{node.id}'})


@mindmaps_bp.route('/<int:map_id>/nodes/<int:node_id>', methods=['PUT'])
def update_node(map_id, node_id):
    node = MindMapNode.query.get_or_404(node_id)
    if node.map_id != map_id:
        abort(404)
    m = MindMap.query.get_or_404(map_id)
    if not _can_access(m):
        return jsonify({'ok': False}), 403
    data = request.get_json(silent=True) or {}
    if 'label' in data:
        node.label = (data['label'] or 'Node')[:200]
    if 'x' in data:
        node.x = float(data['x'])
    if 'y' in data:
        node.y = float(data['y'])
    if 'color' in data and data['color']:
        node.color = data['color']
    db.session.commit()
    return jsonify({'ok': True})


@mindmaps_bp.route('/<int:map_id>/nodes/<int:node_id>', methods=['DELETE'])
def delete_node(map_id, node_id):
    node = MindMapNode.query.get_or_404(node_id)
    if node.map_id != map_id:
        abort(404)
    m = MindMap.query.get_or_404(map_id)
    if not _can_access(m):
        return jsonify({'ok': False}), 403
    # Delete edges involving this node
    MindMapEdge.query.filter(
        (MindMapEdge.source_node_id == node_id) | (MindMapEdge.target_node_id == node_id)
    ).delete()
    db.session.delete(node)
    db.session.commit()
    return jsonify({'ok': True})


@mindmaps_bp.route('/<int:map_id>/edges', methods=['POST'])
def add_edge(map_id):
    m = MindMap.query.get_or_404(map_id)
    if not _can_access(m):
        return jsonify({'ok': False}), 403
    data = request.get_json(silent=True) or {}
    src_cy = data.get('source', '')
    tgt_cy = data.get('target', '')
    if not src_cy.startswith('n') or not tgt_cy.startswith('n'):
        return jsonify({'ok': False, 'error': 'Invalid IDs'}), 400
    src_id = int(src_cy[1:])
    tgt_id = int(tgt_cy[1:])
    edge = MindMapEdge(
        map_id=map_id,
        source_node_id=src_id,
        target_node_id=tgt_id,
        label=(data.get('label') or '')[:200]
    )
    db.session.add(edge)
    db.session.commit()
    return jsonify({'ok': True, 'id': edge.id, 'cy_id': f'e{edge.id}'})


@mindmaps_bp.route('/<int:map_id>/edges/<int:edge_id>', methods=['DELETE'])
def delete_edge(map_id, edge_id):
    edge = MindMapEdge.query.get_or_404(edge_id)
    if edge.map_id != map_id:
        abort(404)
    m = MindMap.query.get_or_404(map_id)
    if not _can_access(m):
        return jsonify({'ok': False}), 403
    db.session.delete(edge)
    db.session.commit()
    return jsonify({'ok': True})


@mindmaps_bp.route('/<int:map_id>/delete', methods=['POST'])
def delete_map(map_id):
    m = MindMap.query.get_or_404(map_id)
    if not _can_access(m):
        abort(403)
    db.session.delete(m)
    db.session.commit()
    return redirect(url_for('mindmaps.list_maps'))
