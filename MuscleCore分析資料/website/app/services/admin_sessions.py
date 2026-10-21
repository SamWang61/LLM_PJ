"""Atomic device revocation, privacy-limited audit and 180-day replay receipt."""
from datetime import timedelta, timezone
from uuid import UUID
from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import PyMongoError
from flask import current_app
from .sku_gateway import CartService, CartError, CartConflict, _member_service
from .member_sessions import revoke_user_sessions
from VibeCart_AI.services.cart_service import utcnow, fingerprint
from VibeCart_AI.MongoDB.admin_session_audit_schema import MIGRATION, RETENTION_SECONDS

REASON = '管理員撤銷會員全部裝置'


def admin_session_service():
    return _member_service(current_app.config.get('ADMIN_SESSION_SERVICE_FACTORY', AdminSessionService))


class AdminSessionService(CartService):
    def _authorize_actor(self, actor_id, mongo_session):
        if not self.authorization_guard or self.authorization_guard.get('role') != 'admin':
            raise PermissionError('Administrator device required')
        try:
            self._authorize_commit(actor_id, mongo_session)
        except CartError:
            raise PermissionError('Administrator authorization revoked') from None

    def revoke(self, actor_id, user_id, *, request_id, reason=REASON):
        try:
            actor, target = ObjectId(actor_id), ObjectId(user_id)
        except (InvalidId, TypeError):
            raise LookupError('Member not found') from None
        try:
            parsed = UUID(request_id)
            if parsed.version != 4 or str(parsed) != request_id:
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise CartError('操作編號無效，請重新開啟會員列表。') from None
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
            raise CartError('操作原因無效。')
        request_hash = fingerprint(['revoke-customer-sessions', str(target), reason])

        def action(s):
            self._authorize_actor(actor, s)
            if not self.db.schema_migrations.find_one({'_id': MIGRATION, 'status': 'succeeded'}, session=s):
                raise PyMongoError('Session audit migration required')
            prior = self.db.admin_write_requests.find_one({'actor_id': actor, 'request_id': request_id}, session=s)
            now = utcnow()
            if prior:
                expiry = prior['expires_at']
                expiry = expiry.replace(tzinfo=timezone.utc) if expiry.tzinfo is None else expiry
                if prior['request_hash'] != request_hash or expiry <= now:
                    raise CartConflict('操作編號已過期或內容不同，請重新開啟會員列表。')
                return prior['result']['revoked_count']
            member = self.db.users.find_one({'_id': target}, session=s)
            if not member:
                raise LookupError('Member not found')
            if member.get('role') != 'customer':
                raise PermissionError('Only customer devices may be revoked')
            # Serialize against concurrent role/account changes without adding user fields.
            previous = member.get('updated_at')
            touch = now
            if previous is not None:
                previous = previous.replace(tzinfo=timezone.utc) if previous.tzinfo is None else previous
                touch = max(now, previous + timedelta(milliseconds=1))
            if self.db.users.update_one({'_id': target, 'role': 'customer'},
                                        {'$set': {'updated_at': touch}}, session=s).matched_count != 1:
                raise PermissionError('Customer authorization changed')
            count = revoke_user_sessions(self.db, target, mongo_session=s)
            self.db.admin_audit_logs.insert_one({
                '_id': ObjectId(), 'schema_version': 4, 'actor_id': actor, 'request_id': request_id,
                'resource_type': 'customer_sessions', 'resource_id': target,
                'before': {'device_count': count}, 'after': {'device_count': 0},
                'reason': reason, 'result': 'succeeded', 'created_at': now}, session=s)
            self.db.admin_write_requests.insert_one({
                '_id': ObjectId(), 'schema_version': 4, 'actor_id': actor, 'request_id': request_id,
                'request_hash': request_hash, 'mode': 'single',
                'result': {'status': 'succeeded', 'http_status': 302, 'revoked_count': count},
                'created_at': now, 'expires_at': now + timedelta(seconds=RETENTION_SECONDS)}, session=s)
            return count

        return self._run(action)
