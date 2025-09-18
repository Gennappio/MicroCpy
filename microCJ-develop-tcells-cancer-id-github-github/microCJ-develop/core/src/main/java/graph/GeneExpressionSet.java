package graph;

import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVRecord;

import java.io.FileReader;
import java.io.IOException;
import java.io.Reader;
import java.util.*;

import static core.SettingsProvider.SETTINGS_PROVIDER;
import static java.util.stream.Collectors.*;

/**
 * Represents a gene expression dataset, be it for a single cell or for a whole subpopulation.
 */
public class GeneExpressionSet {
	private final String subpopulation;

	/* if this expression set is for a cluster and spatial setting is true, it will have an element per cell,
	if it's for a single cell it will have just one element, otherwise it will be empty. */
	private final List<String> cellIdentities = new ArrayList<>();
	private final Map<String, GeneExpression> geneExpressionMap = new HashMap<>(); //key: gene tag

	public GeneExpressionSet(String subpopulation, String... cellIdentities) {
		this.subpopulation = subpopulation;
		Collections.addAll(this.cellIdentities, cellIdentities);
	}

	public String getSubpopulation() {
		return subpopulation;
	}

	public List<String> getCellIdentities() {
		return cellIdentities;
	}

	public boolean getSignForGene(String tag) {
		return geneExpressionMap.get(tag).sign;
	}

	public int getProbabilityForGene(String tag) {
		return geneExpressionMap.get(tag).p;
	}

	public List<String> getAllTags(){
		return new ArrayList<>(geneExpressionMap.keySet());
	}

	public boolean contains(String tag) {
		return geneExpressionMap.containsKey(tag);
	}

	public static List<GeneExpressionSet> parseSingleCellData(String prefix) {
		List<GeneExpressionSet> groups = new ArrayList<>();

		try {
			String id = SETTINGS_PROVIDER.getString("gene-status-data.id", "");
			Reader in = new FileReader("sc/" + prefix + id + "_cells_probabilistic_status.csv");
			var records = CSVFormat.DEFAULT.withFirstRecordAsHeader().parse(in);
			var genes = records.getHeaderMap().keySet();
			genes.remove("cell");
			genes.remove("cluster");
			for (CSVRecord record : records) {
				GeneExpressionSet set = new GeneExpressionSet(record.get("cluster"), record.get("cell"));
				for (String gene : genes) {
					int p = Integer.parseInt(record.get(gene));
					if (p != 0) {
						GeneExpression geneExpression = new GeneExpression(p > 0, Math.abs(p));
						set.geneExpressionMap.put(gene, geneExpression);
					}
				}
				groups.add(set);
			}
		} catch (IOException e) {
			e.printStackTrace();
		}
		return groups;
	}

	public static Map<GeneExpressionSet, Integer> parseClusterData(String prefix) {
		Map<GeneExpressionSet, Integer> clusters = new HashMap<>();
		String id = SETTINGS_PROVIDER.getString("gene-status-data.id", "");
		try {
			Reader in = new FileReader("sc/" + prefix + id + "_cluster_probabilistic_status.csv");
			var records = CSVFormat.DEFAULT.withFirstRecordAsHeader().parse(in);
			var genes = records.getHeaderMap().keySet();
			genes.remove("cluster");
			genes.remove("n");
			for (CSVRecord record : records) {
				GeneExpressionSet set = new GeneExpressionSet(record.get("cluster"));
				int count = Integer.parseInt(record.get("n"));
				for (String gene : genes) {
					int p = Integer.parseInt(record.get(gene));
					if (p != 0) {
						GeneExpression geneExpression = new GeneExpression(p > 0, Math.abs(p));
						set.geneExpressionMap.put(gene, geneExpression);
					}
				}
				clusters.put(set, count);
			}
		} catch (IOException e) {
			e.printStackTrace();
		}

		if (SETTINGS_PROVIDER.getBoolean("gene-status-data.spatial")) { //add list of cell identities belonging to this cluster
			Map<String, Set<String>> identitiesInClustersMap = new HashMap<>();
			try {
				Reader identityReader = new FileReader("sc/" + prefix + "_" + id + "_cluster_identities.csv");
				identitiesInClustersMap = CSVFormat.DEFAULT.withFirstRecordAsHeader().parse(identityReader)
						.getRecords().stream()
						.collect(groupingBy(record -> record.get(1), HashMap::new, mapping(record -> record.get(0), toSet())));
			} catch (IOException e) {
				e.printStackTrace();
			}
			for (GeneExpressionSet cluster : clusters.keySet()) {
				cluster.cellIdentities.addAll(identitiesInClustersMap.get(cluster.getSubpopulation()));
			}
		}
		return clusters;
	}

	private record GeneExpression(boolean sign, int p) {
	}
}
