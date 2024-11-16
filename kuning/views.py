from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages

# dummy data
DUMMY_USERS = [
    {
        "nama": "Rakabima",
        "password": "12",
        "gender": "L",
        "phone": "123",
        "birthdate": "1990-01-01",
        "address": "Jl. Merdeka No.123, Jakarta",
        "saldo" : 100000,
        "role": "pengguna",
    },
{
        "nama": "Safira",
        "password": "12",
        "gender": "P",
        "phone": "124",
        "birthdate": "1995-05-15",
        "address": "Jl. Harmoni Raya No.456, Tegal",
        "bank_name": "GoPay",
        "no_rekening": "1234567890",
        "npwp": "01.123.456.7-891.000",
        "saldo" : 200000,
        "photo_url": "https://example.com/jane_doe.jpg",
        "role": "pekerja",
        "rating" : 4.1,
        "orders_completed" : 100,
        "job_categories" : ['House Cleaning', 'Office Cleaning'],
    }
]

# Fungsi untuk autentikasi user berdasarkan data dummy
def authenticate_dummy(phone, password):
    for user in DUMMY_USERS:
         if user["phone"] == phone and user["password"] == password:
            return user
    return None

def main_view(request):
    return render(request, 'main.html')

def login_view(request):
    if request.method == "POST":
        phone = request.POST.get("phone")
        password = request.POST.get("password")

        # Autentikasi dummy
        user = authenticate_dummy(phone, password)

        if user:
            # Simpan data user ke session
            request.session["user"] = user
            return redirect("homepage") 
    return render(request, "login.html")

def register_view(request):
    if request.user.is_authenticated:
        return redirect('homepage')
        
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('homepage')
    else:
        form = UserCreationForm()
    
    return render(request, 'registration.html', {'form': form})

def logout_view(request):
    logout(request) 
    return redirect('main')  

def edit_profile(request):
    return render(request, "profile.html")