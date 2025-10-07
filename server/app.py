from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
import logging
import requests
import time
import secrets
# bromelia.py is the local module that exports `client` and `initial_messages`.
# Import from it directly so deployments that don't rename the file succeed.
from bromelia import client, initial_messages

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Configure CORS to allow requests from Expo development server
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "allow_headers": ["Content-Type"],
        "supports_credentials": True
    }
})

# Supabase configuration (server-side only)
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')

def _push_rows_to_supabase(rows):
    """Post list of rows to Supabase REST endpoint for `chat_logs`.
    Each row should be a dict matching column names: user_id, message_id, text, sender, timestamp
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        logger.warning('Supabase config not set; will not push rows')
        return False, 'Supabase not configured'
    try:
        endpoint = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chat_logs"
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'apikey': SUPABASE_SERVICE_KEY,
            'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
            # Prefer header can be adjusted; return minimal for performance
            'Prefer': 'return=minimal'
        }
        logger.info('Pushing %d row(s) to Supabase endpoint: %s', len(rows), endpoint)
        resp = requests.post(endpoint, json=rows, headers=headers, timeout=30)
        if resp.status_code in (200, 201, 204):
            return True, None

        # Log status and body for troubleshooting (don't log service key)
        body_preview = resp.text[:2000] if resp.text else ''
        logger.error('Supabase insert failed: status=%s body=%s', resp.status_code, body_preview)

        # If Supabase returned a server error (502/5xx), try per-row insert to isolate bad rows
        if resp.status_code >= 500:
            failed = []
            for idx, row in enumerate(rows):
                try:
                    r = requests.post(endpoint, json=[row], headers=headers, timeout=30)
                    if r.status_code not in (200, 201, 204):
                        logger.error('Per-row insert failed index=%d status=%s body=%s', idx, r.status_code, (r.text or '')[:1000])
                        failed.append({'index': idx, 'status': r.status_code, 'body': (r.text or '')[:2000]})
                except Exception as ex:
                    logger.exception('Exception during per-row insert for index=%d', idx)
                    failed.append({'index': idx, 'error': str(ex)})

            return False, {'bulk_status': resp.status_code, 'bulk_body': body_preview, 'per_row_failures': failed}

        return False, body_preview
    except Exception as e:
        logger.exception('Exception while pushing to Supabase')
        return False, str(e)


@app.route('/', methods=['GET'])
def health_check():
    logger.info("Health check endpoint called")
    return jsonify({
        'status': 'healthy',
        'groq_api_key_configured': bool(os.environ.get('GROQ_API_KEY')),
        'environment': os.environ.get('FLASK_ENV', 'production')
    })

# Verify Groq API key is set
if not os.environ.get('GROQ_API_KEY'):
    logger.error("GROQ_API_KEY environment variable is not set")
    raise ValueError("GROQ_API_KEY environment variable must be set")

logger.info("Starting Flask application with configuration:")
logger.info(f"GROQ_API_KEY configured: {'Yes' if os.environ.get('GROQ_API_KEY') else 'No'}")
logger.info(f"FLASK_ENV: {os.environ.get('FLASK_ENV', 'production')}")
logger.info("CORS configured for all origins")

@app.route('/chat', methods=['POST'])
def chat():
    try:
        logger.info("Received chat request")
        data = request.json
        message = data.get('message')
        if not message:
            logger.error("No message provided in request")
            return jsonify({'error': 'Message is required'}), 400

        messages = initial_messages.copy()
        messages.append({"role": "user", "content": message})

        logger.info("Sending request to Groq API")
        # Retry on transient errors (e.g. 503) with exponential backoff
        max_retries = 3
        backoff = 1
        response = None
        last_exception = None
        for attempt in range(1, max_retries + 1):
            try:
                completion = client.chat.completions.create(
                    model="llama3-70b-8192",
                    messages=messages,
                    temperature=1.10,
                    max_tokens=1800,
                    top_p=1,
                    stream=False,
                    stop=None
                )
                response = completion.choices[0].message.content
                break
            except Exception as e:
                last_exception = e
                msg = str(e) or ''
                logger.warning('Groq request failed attempt %d/%d: %s', attempt, max_retries, msg)
                # If it's not the last attempt, backoff and retry
                if attempt < max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                    continue

                # On last attempt, extract rich details from the exception if available
                detail = None
                try:
                    resp_obj = getattr(e, 'response', None)
                    if resp_obj is not None:
                        # requests-like response object
                        status_code = getattr(resp_obj, 'status_code', None)
                        body = None
                        try:
                            body = getattr(resp_obj, 'text', None) or getattr(resp_obj, 'body', None)
                        except Exception:
                            body = None
                        detail = f"status={status_code} body={body}"
                except Exception:
                    detail = None

                if not detail:
                    # fallback to string/representation of exception
                    try:
                        detail = msg or repr(e)
                    except Exception:
                        detail = 'Unknown error'

                # Classify 503/service-unavailable cases explicitly
                lowered = (detail or '').lower()
                if '503' in lowered or 'service unavailable' in lowered or 'serviceunavailable' in lowered or 'service_unavailable' in lowered:
                    logger.error('Groq service unavailable after %d attempts: %s', attempt, detail)
                    return jsonify({'error': 'service_unavailable', 'details': detail}), 503

                logger.exception('Groq request permanently failed: %s', detail)
                return jsonify({
                    'error': 'An error occurred while processing your request',
                    'details': detail
                }), 500

        logger.info("Successfully received response from Groq API")
        return jsonify({'response': response})

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'An error occurred while processing your request',
            'details': str(e)
        }), 500


@app.route('/logs', methods=['POST'])
def logs():
    """Accepts a batch of messages and inserts them into Supabase chat_logs table.
    Expected JSON: { userId: string, messages: [{ id, text, sender, timestamp }, ...] }
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return jsonify({'error': 'Supabase is not configured on the server'}), 501
    data = request.json or {}
    user_id = data.get('userId') or data.get('user_id')
    messages = data.get('messages')
    if not user_id or not isinstance(messages, list):
        return jsonify({'error': 'userId and messages array are required'}), 400

    rows = []
    for m in messages:
        try:
            rows.append({
                'user_id': user_id,
                'message_id': m.get('id') or m.get('message_id'),
                'text': m.get('text'),
                'sender': m.get('sender'),
                'timestamp': m.get('timestamp')
            })
        except Exception:
            continue

    ok, err = _push_rows_to_supabase(rows)
    if not ok:
        return jsonify({'error': 'Failed to insert rows', 'details': err}), 500
    return jsonify({'status': 'ok', 'inserted': len(rows)}), 200


@app.route('/logs/message', methods=['POST'])
def logs_message():
    """Accepts a single message: { userId: string, message: { id, text, sender, timestamp } }"""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return jsonify({'error': 'Supabase is not configured on the server'}), 501
    data = request.json or {}
    user_id = data.get('userId') or data.get('user_id')
    m = data.get('message')
    if not user_id or not isinstance(m, dict):
        return jsonify({'error': 'userId and message are required'}), 400

    row = {
        'user_id': user_id,
        'message_id': m.get('id') or m.get('message_id'),
        'text': m.get('text'),
        'sender': m.get('sender'),
        'timestamp': m.get('timestamp')
    }

    ok, err = _push_rows_to_supabase([row])
    if not ok:
        return jsonify({'error': 'Failed to insert message', 'details': err}), 500
    return jsonify({'status': 'ok'}), 200


# --- Archive endpoints: store/retrieve encrypted conversation blobs (per-chat archives) ---
def _supabase_headers():
    return {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'apikey': SUPABASE_SERVICE_KEY,
        'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
        'Prefer': 'return=minimal'
    }

def _get_or_create_user_archives(user_id):
    """Get user's archive record or create if not exists"""
    endpoint = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chat_archives?user_id=eq.{user_id}"
    resp = requests.get(endpoint, headers=_supabase_headers(), timeout=20)
    if resp.status_code == 200:
        rows = resp.json()
        if rows:
            return True, rows[0]
        # Create new row for user
        payload = [{'user_id': user_id}]
        resp = requests.post(endpoint, json=payload, headers=_supabase_headers(), timeout=30)
        if resp.status_code in (200, 201, 204):
            # Fetch the newly created row
            resp = requests.get(endpoint, headers=_supabase_headers(), timeout=20)
            if resp.status_code == 200:
                return True, resp.json()[0]
    return False, resp.text

def _find_next_empty_slot(archive_row):
    """Find next available chat_id/link slot (1-32) in the archive row"""
    for i in range(1, 33):
        if not archive_row.get(f'chat_id_{i}'):
            return i
    return None

def _insert_archive(user_id, chat_id, chat_link, chat_name=None):
    """Insert or update chat archive entry. If the chat_id already exists in any user's archive, overwrite that slot.
    Otherwise, insert into the next available slot for the specified user (creating the user archive row if needed).
    """
    # First, try to find if this chat_id already exists anywhere and overwrite that slot
    try:
        endpoint_all = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chat_archives"
        resp_all = requests.get(endpoint_all, headers=_supabase_headers(), timeout=20)
        if resp_all.status_code == 200:
            rows = resp_all.json()
            for row in rows:
                user_row_id = row.get('user_id')
                for i in range(1, 33):
                    if row.get(f'chat_id_{i}') == chat_id:
                        # Overwrite existing slot
                        patch_endpoint = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chat_archives?user_id=eq.{user_row_id}"
                        payload = {
                            f'chat_id_{i}': chat_id,
                            f'chat_link_{i}': chat_link
                        }
                        if chat_name:
                            payload[f'chatname_{i}'] = chat_name
                        patch_resp = requests.patch(patch_endpoint, json=payload, headers=_supabase_headers(), timeout=30)
                        return patch_resp.status_code, patch_resp.text
    except Exception as e:
        logger.exception('Error while checking existing archives for chat_id overwrite')
        # continue to insertion path as best-effort

    # If not found, proceed to insert into the user's archive row
    ok, row = _get_or_create_user_archives(user_id)
    if not ok:
        return 500, "Failed to get/create archive record"

    # Find next empty slot
    slot = _find_next_empty_slot(row)
    if not slot:
        # No free slot: evict the first occupied slot and reuse it (best-effort)
        evict_slot = None
        evict_chat_id = None
        for i in range(1, 33):
            if row.get(f'chat_id_{i}'):
                evict_slot = i
                evict_chat_id = row.get(f'chat_id_{i}')
                break
        if not evict_slot:
            return 400, "No available slots (max 32 chats)"

        # Attempt to delete the storage object for the evicted chat (best-effort)
        try:
            file_name = f"{user_id}_{evict_chat_id}.json.enc"
            storage_url = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/chat_archives/{file_name}"
            del_headers = {'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}', 'apikey': SUPABASE_SERVICE_KEY}
            del_resp = requests.delete(storage_url, headers=del_headers, timeout=30)
            if del_resp.status_code not in (200, 204, 404):
                logger.warning('Storage deletion for evicted chat returned status=%s body=%s', del_resp.status_code, (del_resp.text or '')[:1000])
        except Exception:
            logger.exception('Exception while deleting storage object for evicted chat_id=%s', evict_chat_id)

        # Reuse the evicted slot
        slot = evict_slot

    # Update the slot. Include chat_name if provided. If the table doesn't have chatname columns, retry without it.
    endpoint = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chat_archives?user_id=eq.{user_id}"
    payload = {
        f'chat_id_{slot}': chat_id,
        f'chat_link_{slot}': chat_link
    }
    if chat_name:
        payload[f'chatname_{slot}'] = chat_name

    resp = requests.patch(endpoint, json=payload, headers=_supabase_headers(), timeout=30)

    # If update failed due to missing column (chatname not present in table), retry without chatname
    if resp.status_code >= 400 and chat_name:
        body = resp.text or ''
        if 'column' in body.lower() or 'does not exist' in body.lower() or 'chatname' in body.lower():
            # retry without chatname key
            payload.pop(f'chatname_{slot}', None)
            resp = requests.patch(endpoint, json=payload, headers=_supabase_headers(), timeout=30)

    return resp.status_code, resp.text

def _list_archives_for_user(user_id):
    """List all non-empty chat_id/link pairs for user"""
    ok, row = _get_or_create_user_archives(user_id)
    if not ok:
        return False, row
    
    # Collect all non-empty chat_id/link pairs
    archives = []
    for i in range(1, 33):
        chat_id = row.get(f'chat_id_{i}')
        chat_link = row.get(f'chat_link_{i}')
        if chat_id and chat_link:
            archives.append({
                'chat_id': chat_id,
                'chat_link': chat_link,
                'slot': i,
                'created_at': row.get('created_at')  # Same for all slots currently
            })
    return True, archives

def _get_archive_by_chat_id(chat_id):
    """Find chat_link by chat_id across all slots"""
    endpoint = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chat_archives"
    resp = requests.get(endpoint, headers=_supabase_headers(), timeout=20)
    if resp.status_code == 200:
        rows = resp.json()
        for row in rows:
            # Search all slots for matching chat_id
            for i in range(1, 33):
                if row.get(f'chat_id_{i}') == chat_id:
                    return True, {
                        'chat_id': chat_id,
                        'chat_link': row.get(f'chat_link_{i}'),
                        'created_at': row.get('created_at')
                    }
        return True, None
    return False, resp.text

def _delete_archive(chat_id):
    """Clear chat_id/link slot containing this chat_id"""
    endpoint = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chat_archives"
    resp = requests.get(endpoint, headers=_supabase_headers(), timeout=20)
    if resp.status_code == 200:
        rows = resp.json()
        for row in rows:
            user_id = row.get('user_id')
            # Find slot with matching chat_id
            for i in range(1, 33):
                if row.get(f'chat_id_{i}') == chat_id:
                    # Clear the slot
                    endpoint = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chat_archives?user_id=eq.{user_id}"
                    payload = {
                        f'chat_id_{i}': None,
                        f'chat_link_{i}': None
                    }
                    resp = requests.patch(endpoint, json=payload, headers=_supabase_headers(), timeout=30)
                    return resp.status_code, resp.text
    return 404, "Chat ID not found"


@app.route('/archive', methods=['POST'])
def create_archive():
    """Accept: { userId, chatId?: string, link: string }
    Returns: { chatId, link }
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return jsonify({'error': 'Supabase is not configured on the server'}), 501
    data = request.json or {}
    user_id = data.get('userId')
    chat_link = data.get('link')
    chat_id = data.get('chatId')
    if not user_id or not chat_link:
        return jsonify({'error': 'userId and link are required'}), 400
    
    # generate chat id if missing
    if not chat_id:
        # Try several times to generate a collision-free id using a secure random source
        chat_id = None
        for _ in range(6):
            candidate = f"jogs-{secrets.token_hex(8)}"
            try:
                ok, existing = _get_archive_by_chat_id(candidate)
                # if query failed to check existence, accept candidate to avoid blocking
                if not ok:
                    chat_id = candidate
                    break
                # if not found (existing is None), use candidate
                if existing is None:
                    chat_id = candidate
                    break
            except Exception:
                chat_id = candidate
                break
        # fallback to uuid if all attempts somehow collide
        if not chat_id:
            import uuid
            chat_id = f"jogs-{uuid.uuid4().hex[:12]}"

    # insert archive into next available slot
    status, text = _insert_archive(user_id, chat_id, chat_link)
    if status == 400:  # No slots available
        return jsonify({'error': text}), 400
    if status not in (200, 201, 204):
        logger.error('Archive insert failed: %s %s', status, (text or '')[:2000])
        return jsonify({'error': 'Failed to insert archive', 'details': text}), 500

    return jsonify({'chatId': chat_id, 'link': chat_link}), 200


@app.route('/archive/list', methods=['GET'])
def list_archives():
    user_id = request.args.get('userId') or request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'userId is required'}), 400
    ok, archives = _list_archives_for_user(user_id)
    if not ok:
        return jsonify({'error': 'Failed to list archives', 'details': archives}), 500
    
    # Archives already limited to 32 by table structure
    return jsonify({'archives': archives}), 200


@app.route('/archive/<chat_id>', methods=['GET'])
def get_archive(chat_id):
    ok, archive = _get_archive_by_chat_id(chat_id)
    if not ok:
        return jsonify({'error': 'Failed to fetch archive', 'details': archive}), 500
    if not archive:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(archive), 200


@app.route('/archive/upload', methods=['POST'])
def upload_archive():
    """Accepts: { userId, chatId, cipher }
    The server uploads the cipher blob to Supabase Storage (bucket 'chat_archives') using the service key
    and then registers the chat_id -> public link in the chat_archives table by calling _insert_archive.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return jsonify({'error': 'Supabase not configured on server'}), 501
    data = request.json or {}
    user_id = data.get('userId')
    chat_id = data.get('chatId')
    cipher = data.get('cipher')
    if not user_id or not chat_id or not cipher:
        return jsonify({'error': 'userId, chatId, and cipher are required'}), 400

    # Best-effort: if a chat_id is provided, attempt to delete any existing archive/storage for it
    try:
        try:
            del_status, del_text = _delete_archive_and_storage(chat_id)
            if del_status in (200, 201, 204):
                logger.info('Existing archive cleared for chat_id=%s before upload', chat_id)
            elif del_status == 404:
                # Nothing to delete, that's fine
                logger.debug('No existing archive to clear for chat_id=%s', chat_id)
            else:
                logger.warning('Attempt to clear existing archive returned status=%s details=%s', del_status, (del_text or '')[:1000])
        except Exception:
            logger.exception('Error while attempting to clear existing archive for chat_id=%s', chat_id)
    except Exception:
        # swallow any unforeseen exceptions here since this is best-effort
        logger.exception('Unexpected error in pre-upload cleanup for chat_id=%s', chat_id)

    # Build file name
    file_name = f"{user_id}_{chat_id}.json.enc"

    # Upload to Supabase Storage via REST using service role key
    try:
        upload_url = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/chat_archives/{file_name}"
        headers = {
            'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
            'apikey': SUPABASE_SERVICE_KEY,
            'Content-Type': 'application/octet-stream'
        }
        # Send raw bytes of the cipher string
        resp = requests.put(upload_url, data=cipher.encode('utf-8'), headers=headers, timeout=30)
        if resp.status_code not in (200, 201, 204):
            body_preview = resp.text[:2000] if resp.text else ''
            logger.error('Storage upload failed: status=%s body=%s', resp.status_code, body_preview)
            return jsonify({'error': 'storage_upload_failed', 'status': resp.status_code, 'body': body_preview}), 500

        # Construct public URL for the uploaded file
        public_url = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/public/chat_archives/{file_name}"

        # Register archive link in chat_archives table
        status, text = _insert_archive(user_id, chat_id, public_url)
        if status not in (200, 201, 204):
            logger.error('Failed to register archive in DB: %s %s', status, (text or '')[:2000])
            return jsonify({'error': 'db_register_failed', 'details': text}), 500

        return jsonify({'ok': True, 'chatId': chat_id, 'link': public_url}), 200

    except Exception as e:
        logger.exception('Exception during /archive/upload')
        return jsonify({'error': 'exception', 'details': str(e)}), 500


def _delete_archive_and_storage(chat_id):
    """Delete the storage object for the given chat_id (if present) and clear the corresponding slot in chat_archives.
    This version retries the DB patch to make sure the slot is cleared even if the first request transiently fails.
    """
    endpoint = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chat_archives"
    try:
        resp = requests.get(endpoint, headers=_supabase_headers(), timeout=20)
        if resp.status_code != 200:
            return 500, 'Failed to query archive rows'
        rows = resp.json()
        for row in rows:
            user_id = row.get('user_id')
            for i in range(1, 33):
                if row.get(f'chat_id_{i}') == chat_id:
                    slot = i

                    # Attempt to delete storage object (best-effort). File name convention used elsewhere.
                    try:
                        file_name = f"{user_id}_{chat_id}.json.enc"
                        storage_url = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/chat_archives/{file_name}"
                        del_headers = {'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}', 'apikey': SUPABASE_SERVICE_KEY}
                        del_resp = requests.delete(storage_url, headers=del_headers, timeout=30)
                        if del_resp.status_code not in (200, 204, 404):
                            logger.warning('Storage deletion returned status=%s body=%s', del_resp.status_code, (del_resp.text or '')[:1000])
                    except Exception:
                        logger.exception('Exception while deleting storage object for chat_id=%s', chat_id)

                    # Clear the chat slot in the archive row with retries
                    patch_endpoint = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chat_archives?user_id=eq.{user_id}"
                    payload = {f'chat_id_{slot}': None, f'chat_link_{slot}': None}
                    last_resp = None
                    for attempt in range(1, 4):
                        try:
                            patch_resp = requests.patch(patch_endpoint, json=payload, headers=_supabase_headers(), timeout=30)
                            last_resp = patch_resp
                            if patch_resp.status_code in (200, 201, 204):
                                logger.info('Cleared archive slot for user=%s slot=%s chat_id=%s', user_id, slot, chat_id)
                                return patch_resp.status_code, patch_resp.text
                            else:
                                logger.warning('Patch attempt %d failed status=%s body=%s', attempt, patch_resp.status_code, (patch_resp.text or '')[:1000])
                        except Exception as ex:
                            logger.exception('Exception while patching archive row attempt %d for user=%s slot=%s', attempt, user_id, slot)
                        time.sleep(1)

                    # If we reach here, patch failed on all attempts; return last response or generic error
                    if last_resp is not None:
                        return last_resp.status_code, last_resp.text
                    return 500, 'Failed to clear archive slot'
        return 404, 'Chat ID not found'
    except Exception as e:
        logger.exception('Exception while querying archive rows')
        return 500, str(e)


@app.route('/archive/sweep', methods=['POST'])
def sweep_archives():
    """Maintenance: scan all archive slots and clear any slot whose storage file is missing (or returns 404).
    This helps recover from cases where storage was removed but the DB slot/link remained, filling the 32 slots.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return jsonify({'error': 'Supabase not configured on server'}), 501

    endpoint = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chat_archives"
    try:
        resp = requests.get(endpoint, headers=_supabase_headers(), timeout=30)
        if resp.status_code != 200:
            return jsonify({'error': 'Failed to list archive rows', 'details': resp.text}), 500

        rows = resp.json()
        cleared = []
        failed = []

        for row in rows:
            user_id = row.get('user_id')
            for i in range(1, 33):
                chat_id = row.get(f'chat_id_{i}')
                chat_link = row.get(f'chat_link_{i}')
                if not chat_id:
                    continue

                # Check if the storage object exists
                file_name = f"{user_id}_{chat_id}.json.enc"
                storage_url = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/chat_archives/{file_name}"
                exists = True
                try:
                    head_resp = requests.head(storage_url, headers={'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}', 'apikey': SUPABASE_SERVICE_KEY}, timeout=20)
                    if head_resp.status_code == 200:
                        exists = True
                    elif head_resp.status_code == 404:
                        exists = False
                    elif head_resp.status_code == 405:
                        # HEAD not allowed; try GET
                        get_resp = requests.get(storage_url, headers={'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}', 'apikey': SUPABASE_SERVICE_KEY}, timeout=20)
                        exists = (get_resp.status_code == 200)
                    else:
                        # Treat other statuses as 'exists' to avoid accidental clears on ambiguous responses
                        exists = True
                except Exception:
                    # On unexpected network errors, assume exists (safer) and skip
                    logger.exception('Error while checking storage existence for %s', storage_url)
                    exists = True

                if not exists:
                    # Clear DB slot
                    patch_endpoint = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chat_archives?user_id=eq.{user_id}"
                    payload = {f'chat_id_{i}': None, f'chat_link_{i}': None}
                    try:
                        patch_resp = requests.patch(patch_endpoint, json=payload, headers=_supabase_headers(), timeout=30)
                        if patch_resp.status_code in (200, 201, 204):
                            cleared.append({'user_id': user_id, 'slot': i, 'chat_id': chat_id})
                        else:
                            failed.append({'user_id': user_id, 'slot': i, 'chat_id': chat_id, 'status': patch_resp.status_code, 'body': (patch_resp.text or '')[:1000]})
                    except Exception as ex:
                        failed.append({'user_id': user_id, 'slot': i, 'chat_id': chat_id, 'error': str(ex)})

        return jsonify({'cleared': cleared, 'failed': failed}), 200

    except Exception as e:
        logger.exception('Exception during archive sweep')
        return jsonify({'error': 'exception', 'details': str(e)}), 500


def _locate_archive_slot(chat_id):
    """Return (ok, dict) where dict contains user_id, slot index, and chat_link if found."""
    endpoint = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chat_archives"
    resp = requests.get(endpoint, headers=_supabase_headers(), timeout=20)
    if resp.status_code != 200:
        return False, resp.text
    rows = resp.json()
    for row in rows:
        user_id = row.get('user_id')
        for i in range(1, 33):
            if row.get(f'chat_id_{i}') == chat_id:
                return True, {'user_id': user_id, 'slot': i, 'chat_link': row.get(f'chat_link_{i}')}
    return True, None


@app.route('/archive/download/<chat_id>', methods=['GET'])
def download_archive(chat_id):
    """Fetch the encrypted cipher blob for the given chat_id from Supabase Storage and return it.
    Returns JSON: { chatId, cipher } where cipher is the UTF-8 decoded content of the stored file.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return jsonify({'error': 'Supabase not configured on the server'}), 501

    ok, info = _locate_archive_slot(chat_id)
    if not ok:
        return jsonify({'error': 'Failed to locate archive', 'details': info}), 500
    if not info:
        return jsonify({'error': 'Not found'}), 404

    user_id = info['user_id']
    # Build storage object path using naming convention
    file_name = f"{user_id}_{chat_id}.json.enc"
    storage_url = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/chat_archives/{file_name}"
    try:
        headers = {'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}', 'apikey': SUPABASE_SERVICE_KEY}
        resp = requests.get(storage_url, headers=headers, timeout=30)
        if resp.status_code == 200:
            # Try to decode as utf-8; if binary, return base64
            try:
                content_text = resp.content.decode('utf-8')
                return jsonify({'chatId': chat_id, 'cipher': content_text}), 200
            except Exception:
                import base64
                b64 = base64.b64encode(resp.content).decode('ascii')
                return jsonify({'chatId': chat_id, 'cipher_base64': b64}), 200
        if resp.status_code == 404:
            return jsonify({'error': 'Not found in storage'}), 404
        return jsonify({'error': 'Failed to fetch storage object', 'status': resp.status_code, 'body': (resp.text or '')[:2000]}), 500
    except Exception as e:
        logger.exception('Exception while downloading archive storage for chat_id=%s', chat_id)
        return jsonify({'error': 'exception', 'details': str(e)}), 500


@app.route('/archive/clear_user/<user_id>', methods=['POST'])
def clear_user_archives(user_id):
    """Delete all storage objects and clear all archive slots for the specified user_id.
    Returns a summary of cleared slots and failures.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return jsonify({'error': 'Supabase not configured on the server'}), 501

    endpoint = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chat_archives?user_id=eq.{user_id}"
    try:
        resp = requests.get(endpoint, headers=_supabase_headers(), timeout=30)
        if resp.status_code != 200:
            return jsonify({'error': 'Failed to fetch user archive row', 'details': resp.text}), 500
        rows = resp.json()
        if not rows:
            return jsonify({'cleared': [], 'failed': []}), 200
        row = rows[0]

        cleared = []
        failed = []
        for i in range(1, 33):
            chat_id = row.get(f'chat_id_{i}')
            if not chat_id:
                continue
            file_name = f"{user_id}_{chat_id}.json.enc"
            storage_url = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/chat_archives/{file_name}"
            # delete storage object (best-effort)
            try:
                del_resp = requests.delete(storage_url, headers={'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}', 'apikey': SUPABASE_SERVICE_KEY}, timeout=30)
                if del_resp.status_code not in (200, 204, 404):
                    logger.warning('Failed to delete storage for user=%s chat_id=%s status=%s', user_id, chat_id, del_resp.status_code)
            except Exception as ex:
                logger.exception('Exception deleting storage for user=%s chat_id=%s', user_id, chat_id)

            # patch DB slot to null
            patch_endpoint = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chat_archives?user_id=eq.{user_id}"
            payload = {f'chat_id_{i}': None, f'chat_link_{i}': None}
            try:
                patch_resp = requests.patch(patch_endpoint, json=payload, headers=_supabase_headers(), timeout=30)
                if patch_resp.status_code in (200, 201, 204):
                    cleared.append({'slot': i, 'chat_id': chat_id})
                else:
                    failed.append({'slot': i, 'chat_id': chat_id, 'status': patch_resp.status_code, 'body': (patch_resp.text or '')[:1000]})
            except Exception as ex:
                logger.exception('Exception patching archive row for user=%s slot=%s', user_id, i)
                failed.append({'slot': i, 'chat_id': chat_id, 'error': str(ex)})

        return jsonify({'cleared': cleared, 'failed': failed}), 200
    except Exception as e:
        logger.exception('Exception during clear_user_archives for user=%s', user_id)
        return jsonify({'error': 'exception', 'details': str(e)}), 500

if __name__ == '__main__':
    if not os.environ.get('GROQ_API_KEY'):
        print("Error: GROQ_API_KEY environment variable is not set")
        exit(1)
    app.run(host='0.0.0.0', port=3001)