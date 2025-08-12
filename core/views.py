from rest_framework.views import APIView
from rest_framework.response import Response


# Create your views here.
class ChatbotView(APIView):
    def get(self, requests, *args, **kwargs):
        return Response({'message':'API chatbot aktif'})