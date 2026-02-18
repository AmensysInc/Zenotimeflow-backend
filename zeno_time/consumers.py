"""
WebSocket consumers for real-time features.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """Consumer for real-time notifications"""
    
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_authenticated:
            self.room_group_name = f"user_{self.user.id}"
            
            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            
            await self.accept()
        else:
            await self.close()
    
    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type', 'message')
        message = text_data_json.get('message', '')
        
        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': message_type,
                'message': message,
                'user_id': str(self.user.id)
            }
        )
    
    # Receive message from room group
    async def notification(self, event):
        message = event['message']
        
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'message': message
        }))


class SchedulerConsumer(AsyncWebsocketConsumer):
    """Consumer for scheduler real-time updates"""
    
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_authenticated:
            # Join company-specific groups based on user's companies
            self.company_groups = await self.get_user_company_groups()
            
            for company_id in self.company_groups:
                group_name = f"scheduler_company_{company_id}"
                await self.channel_layer.group_add(
                    group_name,
                    self.channel_name
                )
            
            await self.accept()
        else:
            await self.close()
    
    async def disconnect(self, close_code):
        # Leave all company groups
        if hasattr(self, 'company_groups'):
            for company_id in self.company_groups:
                group_name = f"scheduler_company_{company_id}"
                await self.channel_layer.group_discard(
                    group_name,
                    self.channel_name
                )
    
    @database_sync_to_async
    def get_user_company_groups(self):
        """Get list of company IDs the user has access to"""
        from scheduler.models import Employee, Company
        from accounts.models import UserRole
        
        company_ids = set()
        
        # Get companies from employee records
        employees = Employee.objects.filter(user=self.user)
        for employee in employees:
            if employee.company:
                company_ids.add(str(employee.company.id))
        
        # Get companies from manager roles
        user_roles = UserRole.objects.filter(
            user=self.user,
            role__in=['admin', 'super_admin', 'operations_manager', 'manager']
        )
        if user_roles.exists():
            # If user is a manager/admin, they can see all companies
            # In production, you might want to filter by specific company assignments
            all_companies = Company.objects.all()
            company_ids.update(str(c.id) for c in all_companies)
        
        return list(company_ids)
    
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        action = text_data_json.get('action')
        
        # Handle different actions (subscribe, unsubscribe, etc.)
        if action == 'subscribe_company':
            company_id = text_data_json.get('company_id')
            if company_id:
                group_name = f"scheduler_company_{company_id}"
                await self.channel_layer.group_add(
                    group_name,
                    self.channel_name
                )
    
    # Receive message from room group
    async def shift_update(self, event):
        """Handle shift update notifications"""
        await self.send(text_data=json.dumps({
            'type': 'shift_update',
            'data': event['data']
        }))
    
    async def time_clock_update(self, event):
        """Handle time clock update notifications"""
        await self.send(text_data=json.dumps({
            'type': 'time_clock_update',
            'data': event['data']
        }))

