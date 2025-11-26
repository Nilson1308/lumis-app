from rest_framework import viewsets, permissions
from .models import WeeklyReport, ClassObservation, MeetingMinute
from .serializers import WeeklyReportSerializer, ClassObservationSerializer, MeetingMinuteSerializer

class WeeklyReportViewSet(viewsets.ModelViewSet):
    queryset = WeeklyReport.objects.all().order_by('-start_date')
    serializer_class = WeeklyReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['author', 'start_date']

    # Auto-atribui o autor ao criar
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

class ClassObservationViewSet(viewsets.ModelViewSet):
    queryset = ClassObservation.objects.all().order_by('-date')
    serializer_class = ClassObservationSerializer
    permission_classes = [permissions.IsAuthenticated]
    # Filtros úteis: Por professor, por turma, ou pelo coordenador que fez
    filterset_fields = ['assignment__teacher', 'assignment__classroom', 'coordinator']

    def perform_create(self, serializer):
        serializer.save(coordinator=self.request.user)

class MeetingMinuteViewSet(viewsets.ModelViewSet):
    queryset = MeetingMinute.objects.all().order_by('-date')
    serializer_class = MeetingMinuteSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['title', 'content'] # Busca textual no conteúdo da ata

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)