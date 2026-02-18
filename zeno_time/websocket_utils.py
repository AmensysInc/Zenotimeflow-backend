"""
Utility functions for sending WebSocket notifications.
"""
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def send_notification_to_user(user_id, message, notification_type='notification'):
    """
    Send a notification to a specific user via WebSocket.
    
    Args:
        user_id: UUID of the user
        message: Message content (dict or string)
        notification_type: Type of notification
    """
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f"user_{user_id}",
            {
                'type': notification_type,
                'message': message
            }
        )


def send_scheduler_update(company_id, update_type, data):
    """
    Send scheduler update to all users subscribed to a company.
    
    Args:
        company_id: UUID of the company
        update_type: Type of update ('shift_update', 'time_clock_update', etc.)
        data: Update data (dict)
    """
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f"scheduler_company_{company_id}",
            {
                'type': update_type,
                'data': data
            }
        )

