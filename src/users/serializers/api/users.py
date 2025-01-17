from typing import Optional

from crum import get_current_user
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from djoser import serializers as djoser_serializers
from rest_framework import serializers
from rest_framework.exceptions import ParseError
from rest_framework.response import Response

from users.jwt.tokens import generate_tokens, add_tokens_to_response
from users.models.profile import Profile
from users.serializers.nested.profile import ProfileShortSerializer, ProfileUpdateSerializer

User = get_user_model()


class RegistrationSerializer(djoser_serializers.UserCreateSerializer):
    """
    User registration serializer.
    """

    email = serializers.EmailField()
    password = serializers.CharField(
        style={'input_type': 'password'},
        write_only=True,
    )

    class Meta(djoser_serializers.UserCreateSerializer.Meta):
        model = User
        fields = ('id', 'first_name', 'last_name', 'username','email', 'password', )

    @staticmethod
    def validate_email(value: str) -> str:
        """Ensure email uniqueness."""
        email = value.lower()
        if User.objects.filter(email=email).exists():
            raise ParseError('A user with this email is already registered.')
        return email

    # def create(self, validated_data):
    #     """Creating user with jwt tokens in cookies"""
    #     user = super().create(validated_data)
    #     access_token, refresh_token = generate_tokens(user)
    #
    #     response = Response("Регистрация прошла успешно.")
    #     add_tokens_to_response(response, access_token, refresh_token)
    #     return response


class UserSerializer(serializers.ModelSerializer):
    """
    User serializer with profile information.
    """

    profile = ProfileShortSerializer()

    class Meta:
        model = User
        fields = (
            'id',
            'first_name',
            'last_name',
            'email',
            'phone_number',
            'username',
            'profile',
            'date_joined',
        )

#
# class CustomActivationSerializer(djoser_serializers.ActivationSerializer):
#     """Serializer for activation user"""
#     pass



class ChangePasswordSerializer(serializers.ModelSerializer):
    """
    Change password serializer

    Аттрибуты:
        * `old_password` (CharField): старый пароль.
        * `new_password` (CharField): новый пароль.
    """

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('old_password', 'new_password')

    def validate(self, attrs: dict[str, str]) -> dict[str, str]:
        """Проверка на корректность """
        user = get_current_user()
        old_password = attrs.pop('old_password')
        if not user.check_password(raw_password=old_password):
            raise ParseError('Проверьте правильность текущего пароля!')
        return attrs

    @staticmethod
    def validate_new_password(password: str) -> str:
        """Проверка на корректность нового пароля."""
        validate_password(password=password)
        return password

    def update(self, instance: User, validated_data: dict[str, str]) -> User:
        """Обновление пароля в модели User."""
        password = validated_data.pop('new_password')
        # Хэшируем пароль
        instance.set_password(raw_password=password)
        instance.save()
        return instance


class PasswordResetSerializer(djoser_serializers.SendEmailResetSerializer):
    """Сериализатор для запроса о новом пароле на почту."""
    pass


class CustomPasswordResetConfirmSerializer(
    djoser_serializers.PasswordResetConfirmSerializer
):
    """Сериализатор для сброса пароля"""
    pass



class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user information.
    """

    profile = ProfileUpdateSerializer()

    class Meta:
        model = User
        fields = (
            'id',
            'first_name',
            'last_name',
            'email',
            'phone_number',
            'username',
            'profile',
        )

    @staticmethod
    def _update_profile(profile: Profile, data: Optional[str]) -> None:
        """Update profile details."""
        profile_serializer = ProfileUpdateSerializer(
            instance=profile, data=data, partial=True
        )
        profile_serializer.is_valid(raise_exception=True)
        profile_serializer.save()

    def update(self, instance: User, validated_data: dict[str, str]) -> User:
        """Update user model and related profile."""
        profile_data = validated_data.pop('profile', None)

        with transaction.atomic():
            instance = super().update(
                instance=instance, validated_data=validated_data
            )
            if profile_data:
                self._update_profile(instance.profile, profile_data)

        return instance


class UserUpdateRoleSerializer(serializers.ModelSerializer):
    """Сериализатор обновления роли."""

    class Meta:
        model = User
        fields = ('id', 'role')

    def update(self, instance: User, validated_data: dict[str, str]) -> User:
        """Обновление роли пользователя."""
        current_role = validated_data.pop('role')
        # Проверка на существующую роль.
        if not any((current_role == role for role, _ in instance.Role.choices)):
            ParseError('Такой роли не существует!')
        if current_role in (instance.Role.ADMIN, instance.Role.MANAGER):
            instance.is_staff = True
        instance.role = current_role
        instance.save()
        return instance


class UserListSearchSerializer(serializers.ModelSerializer):
    """Сериализатор поиска пользователей."""
    class Meta:
        model = User
        fields = ('id',
            'first_name',
            'last_name',
            'email',
            'phone_number',
            'username',
            'is_active',)

#