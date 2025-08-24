"""
WebSocket consumers for real-time dashboard updates
"""
import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .docker_utils import DockerSwarmManager


class DashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add(
            "dashboard_updates",
            self.channel_name
        )
        await self.accept()
        
        # Start sending periodic updates
        self.update_task = asyncio.create_task(self.send_periodic_updates())

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            "dashboard_updates",
            self.channel_name
        )
        
        # Cancel the update task
        if hasattr(self, 'update_task'):
            self.update_task.cancel()

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'get_services':
            await self.send_services_update()
        elif message_type == 'get_nodes':
            await self.send_nodes_update()
        elif message_type == 'get_system_info':
            await self.send_system_info_update()

    async def send_periodic_updates(self):
        """Send periodic updates to the client"""
        while True:
            try:
                await asyncio.sleep(5)  # Update every 5 seconds
                await self.send_services_update()
                await self.send_nodes_update()
                await self.send_system_info_update()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in periodic updates: {e}")
                await asyncio.sleep(5)

    @database_sync_to_async
    def get_docker_data(self):
        """Get Docker data synchronously"""
        docker_manager = DockerSwarmManager()
        return {
            'services': docker_manager.get_services(),
            'nodes': docker_manager.get_nodes(),
            'system_info': docker_manager.get_system_info(),
            'swarm_info': docker_manager.get_swarm_info(),
            'swarm_active': docker_manager.is_swarm_active()
        }

    async def send_services_update(self):
        """Send services data to client"""
        try:
            data = await self.get_docker_data()
            await self.send(text_data=json.dumps({
                'type': 'services_update',
                'data': data['services']
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Failed to get services data: {str(e)}'
            }))

    async def send_nodes_update(self):
        """Send nodes data to client"""
        try:
            data = await self.get_docker_data()
            await self.send(text_data=json.dumps({
                'type': 'nodes_update',
                'data': data['nodes']
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Failed to get nodes data: {str(e)}'
            }))

    async def send_system_info_update(self):
        """Send system info data to client"""
        try:
            data = await self.get_docker_data()
            await self.send(text_data=json.dumps({
                'type': 'system_info_update',
                'data': {
                    'system_info': data['system_info'],
                    'swarm_info': data['swarm_info'],
                    'swarm_active': data['swarm_active']
                }
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Failed to get system info: {str(e)}'
            }))