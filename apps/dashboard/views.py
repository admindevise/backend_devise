from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.shortcuts import redirect




@method_decorator(login_required, name='dispatch')
class Dashboard1View(View):
    template_name = 'dashboard_1.html'
    url_name = 'devise-dashboard1'

    def get(self, request, *args, **kwargs):
        context = {}
        context['companies'] = "xxx"
        context['nav_inicio'] = True
        return render(request, self.template_name, context)
    
    # def dispatch(self, request, *args, **kwargs):
    #     if not request.user.is_authenticated:
    #         # This will redirect to the login view
    #         return self.handle_no_permission()
    #     if not self.request.user.is_superuser:
    #         # Redirect the user to somewhere else - add your URL here
    #         return redirect('/auth/logout/')

    #     # Checks pass, let http method handlers process the request
    #     return super().dispatch(request, *args, **kwargs)
