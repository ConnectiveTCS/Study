from flask import render_template, request, redirect, url_for, abort, flash
from flask_login import current_user, login_required
from . import groups_bp
from app.extensions import db
from app.models.group import StudyGroup, GroupMember


@groups_bp.route('/')
@login_required
def list_groups():
    memberships = GroupMember.query.filter_by(user_id=current_user.id).all()
    my_groups = [m.group for m in memberships]
    return render_template('groups/list.html', groups=my_groups)


@groups_bp.route('/new', methods=['POST'])
@login_required
def new_group():
    name = (request.form.get('name') or '').strip()[:100]
    if not name:
        return redirect(url_for('groups.list_groups'))
    desc = (request.form.get('description') or '')[:500]
    group = StudyGroup(name=name, description=desc, created_by=current_user.id)
    db.session.add(group)
    db.session.flush()
    member = GroupMember(group_id=group.id, user_id=current_user.id, role='owner')
    db.session.add(member)
    db.session.commit()
    return redirect(url_for('groups.detail', group_id=group.id))


@groups_bp.route('/join', methods=['POST'])
@login_required
def join_group():
    code = (request.form.get('invite_code') or '').strip()
    group = StudyGroup.query.filter_by(invite_code=code).first()
    if not group:
        flash('Invalid invite code.', 'error')
        return redirect(url_for('groups.list_groups'))
    already = GroupMember.query.filter_by(group_id=group.id, user_id=current_user.id).first()
    if not already:
        member = GroupMember(group_id=group.id, user_id=current_user.id, role='member')
        db.session.add(member)
        db.session.commit()
    return redirect(url_for('groups.detail', group_id=group.id))


@groups_bp.route('/<int:group_id>')
@login_required
def detail(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    membership = GroupMember.query.filter_by(group_id=group_id, user_id=current_user.id).first()
    if not membership:
        abort(403)
    members = group.members.all()
    return render_template('groups/detail.html', group=group, members=members, membership=membership)


@groups_bp.route('/<int:group_id>/leave', methods=['POST'])
@login_required
def leave_group(group_id):
    membership = GroupMember.query.filter_by(group_id=group_id, user_id=current_user.id).first_or_404()
    if membership.role == 'owner':
        # Transfer ownership or delete if sole member
        other = GroupMember.query.filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id != current_user.id
        ).first()
        if other:
            other.role = 'owner'
        else:
            group = StudyGroup.query.get(group_id)
            db.session.delete(group)
            db.session.commit()
            return redirect(url_for('groups.list_groups'))
    db.session.delete(membership)
    db.session.commit()
    return redirect(url_for('groups.list_groups'))


@groups_bp.route('/<int:group_id>/delete', methods=['POST'])
@login_required
def delete_group(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    membership = GroupMember.query.filter_by(group_id=group_id, user_id=current_user.id, role='owner').first()
    if not membership:
        abort(403)
    db.session.delete(group)
    db.session.commit()
    return redirect(url_for('groups.list_groups'))
