import numpy as np
import litellm
from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings
from sentence_transformers import SentenceTransformer
from umap import UMAP
import hdbscan
from sklearn.neighbors import NearestNeighbors
from tqdm import tqdm

from jao_backend.skills.models import Skill, SkillCluster
from jao_backend.common.litellm.model_list import ModelLister

class Command(BaseCommand):
    help = "Modular pipeline to cluster skills and name the resulting groups."

    def add_arguments(self, parser):
        parser.add_argument('--cluster', action='store_true', help='Run UMAP/HDBSCAN clustering math.')
        parser.add_argument('--name', action='store_true', help='Run LLM naming loop for unnamed clusters.')
        parser.add_argument('--clear', action='store_true', help='Reset all clusters and delete SkillCluster records.')

    def handle(self, *args, **options):
        # 1. Action: Clear
        if options['clear']:
            self.stdout.write(self.style.WARNING("Clearing existing cluster data..."))
            with transaction.atomic():
                Skill.objects.all().update(cluster_id=-1)
                SkillCluster.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Database reset complete."))

        # 2. Action: Cluster
        if options['cluster']:
            self.run_clustering()

        # 3. Action: Name
        if options['name']:
            self.run_naming()

        if not any([options['cluster'], options['name'], options['clear']]):
            self.stdout.write("No flags provided. Use --cluster, --name, or --clear.")

    def run_clustering(self):
        self.stdout.write("--- Starting Clustering Phase ---")
        skills = list(Skill.objects.all())
        names = [s.name for s in skills]

        if len(names) < 10:
            self.stdout.write(self.style.ERROR("Not enough skills to cluster."))
            return

        # Math Logic
        model = SentenceTransformer("all-MiniLM-L6-v2")
        embeddings = model.encode(names, show_progress_bar=True)
        
        umap_embeddings = UMAP(n_neighbors=15, n_components=2, min_dist=0.0, random_state=42).fit_transform(embeddings)
        labels = hdbscan.HDBSCAN(min_cluster_size=5).fit_predict(umap_embeddings)

        # Handle Noise
        valid_mask = labels != -1
        if np.any(valid_mask) and np.any(~valid_mask):
            knn = NearestNeighbors(n_neighbors=1).fit(umap_embeddings[valid_mask])
            noise_idx = np.where(labels == -1)[0]
            _, nearest = knn.kneighbors(umap_embeddings[noise_idx])
            labels[noise_idx] = labels[valid_mask][nearest.flatten()]

        # Save to DB
        clusters_found = np.unique(labels)
        with transaction.atomic():
            for c_id in clusters_found:
                SkillCluster.objects.get_or_create(cluster_id=int(c_id), defaults={'name': f"Cluster {c_id}"})
            for c_id in clusters_found:
                ids = [skills[i].id for i in np.where(labels == c_id)[0]]
                Skill.objects.filter(id__in=ids).update(cluster_id=int(c_id))
        
        self.stdout.write(self.style.SUCCESS(f"Clustered {len(names)} skills into {len(clusters_found)} groups."))

    def run_naming(self):
        self.stdout.write("--- Starting Naming Phase ---")
        
        # Check if the LLM provider is actually reachable using your ModelLister
        if not ModelLister.is_available():
            self.stdout.write(self.style.ERROR(f"AI Provider ({settings.LITELLM_CUSTOM_PROVIDER}) is not reachable!"))
            return

        unnamed = SkillCluster.objects.filter(name__startswith="Cluster ")
        if not unnamed.exists():
            self.stdout.write("No clusters need naming.")
            return

        # Prepare model string correctly for LiteLLM
        raw_model = settings.LITELLM_COMPLETION_MODEL
        full_model_name = ModelLister.get_litellm_model_name(raw_model)

        for cluster in tqdm(unnamed, desc="AI Naming"):
            skill_sample = list(Skill.objects.filter(cluster_id=cluster.cluster_id).values_list('name', flat=True)[:30])
            
            try:
                response = litellm.completion(
                    model=full_model_name,
                    messages=[
                        {"role": "system", "content": "Return ONLY a 2-3 word category name for these skills."},
                        {"role": "user", "content": f"Skills: {', '.join(skill_sample)}"}
                    ],
                    max_tokens=15, temperature=0.1
                )
                name = response.choices[0].message.content.strip().replace('"', '')
                if name:
                    cluster.name = name
                    cluster.save()
            except Exception as e:
                self.stderr.write(f"Error at Cluster {cluster.cluster_id}: {e}")

        self.stdout.write(self.style.SUCCESS("Naming complete!"))