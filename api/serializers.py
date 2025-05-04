from rest_framework import serializers
from .models import Category, Transaction, Budget
from django.contrib.auth.models import User

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class TransactionSerializer(serializers.ModelSerializer):
    category = CategorySerializer()

    class Meta:
        model = Transaction
        fields = ['id', 'category', 'amount', 'date', 'description', 'transaction_type']

    def create(self, validated_data):
        category_data = validated_data.pop('category')
        category, _ = Category.objects.get_or_create(name=category_data['name'], user=self.context['request'].user)
        transaction = Transaction.objects.create(category=category, **validated_data)
        return transaction

    def update(self, instance, validated_data):
        # Handle nested category field
        category_data = validated_data.pop('category', None)
        if category_data:
            category, _ = Category.objects.get_or_create(name=category_data['name'], user=self.context['request'].user)
            instance.category = category

        # Update other fields
        instance.amount = validated_data.get('amount', instance.amount)
        instance.date = validated_data.get('date', instance.date)
        instance.description = validated_data.get('description', instance.description)
        instance.transaction_type = validated_data.get('transaction_type', instance.transaction_type)
        instance.save()
        return instance

class BudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = ['id', 'amount', 'month']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'password']
        extra_kwargs = {
            'password': {'write_only': True},
            'username': {'required': True, 'allow_blank': False},
        }

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user