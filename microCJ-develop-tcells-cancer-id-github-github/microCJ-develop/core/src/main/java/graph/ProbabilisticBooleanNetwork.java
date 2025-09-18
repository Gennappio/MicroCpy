package graph;

import org.jgrapht.io.Attribute;
import org.jgrapht.io.GraphImporter;
import org.jgrapht.io.VertexProvider;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;

public final class ProbabilisticBooleanNetwork extends SynchronousBooleanNetwork{
	private ProbabilisticBooleanNetwork(String filename, boolean randomiseDecisionWindow) {
		super(filename, randomiseDecisionWindow, createImporter());
	}

	public static Network randomlyActivatedGraph(String filename, boolean randomiseDecisionWindow, String initial){
		return new ProbabilisticBooleanNetwork(filename, randomiseDecisionWindow).turnNodes(false).activateGenes(initial);
	}

	@Override
	public boolean mutate(double mutationChance) {
		boolean mutated = false;
		ThreadLocalRandom random = ThreadLocalRandom.current();
		int rg = random.nextInt(getGenes().size());

		for (Gene gene : getGenes()) {
			if(rg-- == 0) { //get a random gene
				double r = random.nextDouble();
				if (r < mutationChance) {
					mutated = true;
					int cuP = gene.getMutation().getP();
					if(cuP == 0) cuP = 1;
					int p = random.nextInt(1000/cuP);
					Mutation mutation = new Mutation(random.nextBoolean(), p);
					gene.applyMutation(mutation);
				}
			}
		}
		return mutated;
	}

	private static GraphImporter<Node, Edge> createImporter() {
		VertexProvider<Node> vertexProvider = (id, attributes) -> {
			String kind = attributes.get("kind").getValue();
			Node v;
			if(kind.equals("input")){
				v = new Input(id);
				Attribute resistance_p = attributes.get("resistance_p");
				((Input)v).setResistanceP(resistance_p == null ? 0 : Integer.parseInt(resistance_p.getValue()));
			}
			else{
				String rule = attributes.get("rule").getValue();
				if(kind.equals("gene")) {
					var ruleStrings = rule.split(",");
					int n = ruleStrings.length;
					if(n > 1){
						List<Rule> rules = new ArrayList<>();
						var ps = attributes.get("p").getValue().split(",");
						for (int i = 0; i < n; i++) {
							int p = Integer.parseInt(ps[i]);
							Rule thisRule = Rule.parser(ruleStrings[i], p);
							rules.add(thisRule);
						}
						v = new Gene(id, rules);
					} else{
						v = new Gene(id, rule);
					}
				}
				else if(kind.equals("fate")){
					v = new FateNode(id, rule);
				}
				else throw new IllegalArgumentException("Wrong kind attribute for a node, must be 'gene', 'input' or 'fate'");
			}
			return v;
		};

		return createImporter(vertexProvider);
	}
}