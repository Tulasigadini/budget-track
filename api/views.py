from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework.pagination import PageNumberPagination
from .models import Category, Transaction, Budget
from .serializers import CategorySerializer, TransactionSerializer, BudgetSerializer, UserSerializer
from django.db.models import Sum
from datetime import datetime
import logging

# Set up logging
logger = logging.getLogger(__name__)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Transaction.objects.filter(user=self.request.user)
        category = self.request.query_params.get('category')
        date = self.request.query_params.get('date')
        amount = self.request.query_params.get('amount')
        if category:
            queryset = queryset.filter(category__name=category)
        if date:
            queryset = queryset.filter(date=date)
        if amount:
            queryset = queryset.filter(amount=amount)
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class BudgetViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Budget.objects.filter(user=self.request.user)
        month = self.request.query_params.get('month')
        if month:
            queryset = queryset.filter(month=month)
        return queryset

    def perform_create(self, serializer):
        month = serializer.validated_data['month']
        amount = serializer.validated_data['amount']
        existing_budget = Budget.objects.filter(user=self.request.user, month=month).first()
        if existing_budget:
            existing_budget.amount = amount
            existing_budget.save()
            serializer.instance = existing_budget
        else:
            serializer.save(user=self.request.user)

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    logger.info(f"Register request data: {request.data}")
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key}, status=status.HTTP_201_CREATED)
    logger.error(f"Registration errors: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    from django.contrib.auth import authenticate
    user = authenticate(username=username, password=password)
    if user:
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key}, status=status.HTTP_200_OK)
    return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def summary(request):
    transactions = Transaction.objects.filter(user=request.user)
    total_income = transactions.filter(transaction_type='income').aggregate(Sum('amount'))['amount__sum'] or 0
    total_expenses = transactions.filter(transaction_type='expense').aggregate(Sum('amount'))['amount__sum'] or 0
    balance = total_income - total_expenses
    current_month = datetime.now().strftime('%Y-%m')
    budget = Budget.objects.filter(user=request.user, month=current_month).first()
    budget_amount = budget.amount if budget else 0
    return Response({
        'total_income': total_income,
        'total_expenses': total_expenses,
        'balance': balance,
        'budget': budget_amount
    })