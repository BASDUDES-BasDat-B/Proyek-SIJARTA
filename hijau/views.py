from django.http import JsonResponse
from django.shortcuts import redirect, render
import json

def homepage(request):
    # Dummy data for categories and subcategories - kept the same as it's well structured
    categories = [
        {'name': 'Cleaning', 'description': 'Professional cleaning services', 'icon': 'fas fa-broom', 'slug': 'cleaning', 'subcategories': [
            {'name': 'House Cleaning', 'slug': 'house-cleaning'},
            {'name': 'Office Cleaning', 'slug': 'office-cleaning'}
        ]},
        {'name': 'Plumbing', 'description': 'Expert plumbing services', 'icon': 'fas fa-wrench', 'slug': 'plumbing', 'subcategories': [
            {'name': 'Pipe Repair', 'slug': 'pipe-repair'},
            {'name': 'Leak Detection', 'slug': 'leak-detection'}
        ]},
        {'name': 'Electrical', 'description': 'Reliable electrical services', 'icon': 'fas fa-bolt', 'slug': 'electrical', 'subcategories': [
            {'name': 'Wiring', 'slug': 'wiring'},
            {'name': 'Lighting', 'slug': 'lighting'}
        ]},
        {'name': 'Gardening', 'description': 'Gardening and landscaping services', 'icon': 'fas fa-seedling', 'slug': 'gardening', 'subcategories': [
            {'name': 'Lawn Mowing', 'slug': 'lawn-mowing'},
            {'name': 'Tree Trimming', 'slug': 'tree-trimming'}
        ]},
    ]

    context = {
        'categories': categories,
    }

    return render(request, 'homepage.html', context)

def subcategory_detail(request, category_slug, subcategory_slug):
    # Find the matching category and subcategory from dummy data
    categories = {
        'cleaning': {
            'name': 'Cleaning',
            'house-cleaning': {
                'name': 'House Cleaning',
                'description': 'Professional house cleaning services for all your needs',
            },
            'office-cleaning': {
                'name': 'Office Cleaning',
                'description': 'Professional office cleaning services',
            }
        },
        # Add other categories as needed
    }
    
    category = categories.get(category_slug, {'name': 'Unknown Category'})
    subcategory = category.get(subcategory_slug, {
        'name': 'Unknown Subcategory',
        'description': 'Service description not available'
    })
    
    service_sessions = [
        {
            'id': 1,
            'name': 'Basic Cleaning (2 hours)',
            'price': '150000'
        },
        {
            'id': 2,
            'name': 'Deep Cleaning (4 hours)',
            'price': '300000'
        },
        {
            'id': 3,
            'name': 'Premium Cleaning (6 hours)',
            'price': '450000'
        }
    ]
    
    workers = [
        {
            'id': 1,
            'name': 'John Doe',
            'profile_picture': None
        },
        {
            'id': 2,
            'name': 'Jane Smith',
            'profile_picture': None
        },
        {
            'id': 3,
            'name': 'Bob Johnson',
            'profile_picture': None
        }
    ]
    
    testimonials = [
        {
            'user_name': 'Alice Cooper',
            'date': '2024-03-10',
            'text': 'Great service! Very thorough and professional.',
            'rating': 5,
            'worker_name': 'John Doe'
        },
        {
            'user_name': 'David Brown',
            'date': '2024-03-08',
            'text': 'Good service but arrived a bit late.',
            'rating': 4,
            'worker_name': 'Jane Smith'
        }
    ]
    
    context = {
        'subcategory': subcategory,
        'category': {'name': category['name']},
        'service_sessions': service_sessions,
        'workers': workers,
        'testimonials': testimonials,
        'is_worker': False,
        'is_joined': False
    }
    
    return render(request, 'subkategori_jasa.html', context)

def view_pesanan(request):
    # Kept the same as it's well structured
    orders = [
        {
            'id': 1,
            'subcategory': {'name': 'House Cleaning'},
            'service_session': {'name': 'Basic Cleaning (2 hours)'},
            'total_payment': '150000',
            'worker': {'name': 'John Doe'},
            'status': 'waiting_payment',
            'has_testimonial': False,
            'get_status_display': 'Menunggu Pembayaran'
        },
        {
            'id': 2,
            'subcategory': {'name': 'House Cleaning'},
            'service_session': {'name': 'Deep Cleaning (4 hours)'},
            'total_payment': '300000',
            'worker': None,
            'status': 'finding_worker',
            'has_testimonial': False,
            'get_status_display': 'Mencari Pekerja Terdekat'
        },
        {
            'id': 3,
            'subcategory': {'name': 'House Cleaning'},
            'service_session': {'name': 'Premium Cleaning (6 hours)'},
            'total_payment': '450000',
            'worker': {'name': 'Jane Smith'},
            'status': 'completed',
            'has_testimonial': False,
            'get_status_display': 'Pesanan Selesai'
        },
        {
            'id': 4,
            'subcategory': {'name': 'House Cleaning'},
            'service_session': {'name': 'Basic Cleaning (2 hours)'},
            'total_payment': '150000',
            'worker': {'name': 'Bob Johnson'},
            'status': 'completed',
            'has_testimonial': True,
            'get_status_display': 'Pesanan Selesai'
        }
    ]
    
    categories = [
        {'id': 1, 'name': 'House Cleaning'},
        {'id': 2, 'name': 'Office Cleaning'},
        {'id': 3, 'name': 'Garden Cleaning'}
    ]
    
    context = {
        'orders': orders,
        'categories': categories,
    }
    
    return render(request, 'view_pesanan.html', context)

def create_order(request):
    if request.method == 'POST':
        return redirect('view_pesanan')
    return redirect('homepage')

def calculate_total(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        session_id = data.get('session_id')
        discount_code = data.get('discount_code')
        
        base_prices = {
            '1': 150000,
            '2': 300000,
            '3': 450000
        }
        
        total = base_prices.get(str(session_id), 0)
        if discount_code:
            total = total * 0.9  # 10% discount
            
        return JsonResponse({'total': f"{total:,.0f}"})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

def create_testimonial(request):
    if request.method == 'POST':
        return redirect('view_pesanan')
    return redirect('homepage')

def cancel_order(request, order_id):
    if request.method == 'POST':
        return JsonResponse({'status': 'success'})
    return JsonResponse({'error': 'Invalid request'}, status=400)