from compass.utils.helper import httpForbidden


def ajax_required(f, method='POST', login_required=True, ajax_required=True):
    """
    AJAX request required decorator
    use it in your views:

    @ajax_required
    def my_view(request):
        ....
    """
    def wrap(request, *args, **kwargs):
        if ajax_required and not request.is_ajax():
            return httpForbidden(403, 'Request must be set via AJAX.')

        if login_required and not request.user.is_authenticated():
            return httpForbidden(403, 'User must be authenticated!')

        return f(request, *args, **kwargs)

    wrap.__doc__ = f.__doc__
    wrap.__name__ = f.__name__
    return wrap
