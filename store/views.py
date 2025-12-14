#store/views.py
from rest_framework import viewsets, permissions, status, mixins
from rest_framework.response import Response
from .models import Service, Transaction
from .serializers import ServiceSerializer, TransactionSerializer, PurchaseSerializer,DepositSerializer
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from django.shortcuts import redirect
from decimal import Decimal
from django.contrib.auth import get_user_model

User = get_user_model()

class ServiceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Service.objects.filter(is_active=True)
    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny] 

class TransactionViewSet(viewsets.GenericViewSet, 
                         mixins.ListModelMixin, 
                         mixins.CreateModelMixin):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user).order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return PurchaseSerializer
        return TransactionSerializer

    def create(self, request, *args, **kwargs):
        # 1. Initialize Serializer with 'request' in context (so we can access user)
        serializer = self.get_serializer(data=request.data, context={'request': request})
        
        # 2. Run Validation
        serializer.is_valid(raise_exception=True)
        
        # 3. Run the Logic (The create method we just wrote)
        transaction_record = serializer.save()

        # 4. Return Custom Response
        return Response({
            "status": "success",
            "result": getattr(transaction_record, 'api_result', 'Processed'),
            "transaction_id": transaction_record.id,
            "new_balance": request.user.balance
        }, status=status.HTTP_201_CREATED)
        
    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny], url_path='callback')
    def kashier_callback(self, request):
        """
        GET /api/store/transactions/callback/
        """
        # 1. Pass the URL parameters (query_params) to the Serializer
        serializer = DepositSerializer(data=request.query_params, context={'request': request})

        try:
            # 2. Run Validation & Creation (All logic is inside .is_valid and .save)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            
            # 3. Success Redirect
            return redirect("https://your-frontend.com/payment-success")

        except Exception as e:
            # 4. Failure Redirect
            # You can print(e) here for debugging logs
            return redirect("https://your-frontend.com/payment-failed")
        