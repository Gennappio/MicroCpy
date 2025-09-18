/*
Copyright 2019 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package graph;

import core.Fate;
import core.SettingsProvider;
import org.jgrapht.Graph;
import org.jgrapht.graph.DefaultDirectedGraph;
import org.jgrapht.io.*;
import org.tinylog.Logger;
import utils.GINMLConverter;

import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.InputStreamReader;
import java.util.*;
import java.util.concurrent.ThreadLocalRandom;
import java.util.function.BiFunction;
import java.util.stream.Collectors;

public class SynchronousBooleanNetwork implements Network {
	private static int decisionWindow;
	private final Graph<Node, Edge> graph;
	private final Map<String, Boolean> currentValues = new HashMap<>();
	private final Map<Node, Boolean> nextUpdate = new HashMap<>();
	private int decisionTimer;
	private boolean decisionTimerActive = false;
	private Fate lastActiveFate;

	/**
	 * Constructs a new instance of Network by importing a graphml file.
	 *
	 * @param filename                the name of the file, which should be placed in the resources folder
	 * @param randomiseDecisionWindow should the decision window be a random number between 0 and the maximum, or should it be the maximum. Useful to make initial cells heterogeneous
	 * @param importer
	 */
	protected SynchronousBooleanNetwork(String filename, boolean randomiseDecisionWindow, GraphImporter<Node, Edge> importer) {
		graph = new DefaultDirectedGraph<>(Edge.class);
		loadGraphFile(filename, graph, importer);
		if(randomiseDecisionWindow) {
			ThreadLocalRandom r = ThreadLocalRandom.current();
			decisionTimer = (int) (decisionWindow * r.nextDouble(0.2, 0.5));
		} else decisionTimer = decisionWindow;
	}

	protected SynchronousBooleanNetwork(String filename, boolean randomiseDecisionWindow){
		this(filename, randomiseDecisionWindow, createImporter());
	}

	@Override
	public Graph<Node, Edge> getGraph() {
		return graph;
	}

	@Override
	public Set<Edge> getEdges() {
		return getGraph().edgeSet();
	}

	@Override
	public Set<Node> getNodes() {
		return getGraph().vertexSet();
	}

	@Override
	public Set<Gene> getGenes() {
		Set<Gene> set = new HashSet<>();
		for (Node node : getNodes()) {
			if (node instanceof Gene) {
				set.add((Gene) node);
			}
		}
		return set;
	}

	@Override
	public Set<Node> getInputs() {
		Set<Node> set = new HashSet<>();
		for (Node node : getNodes()) {
			if (node instanceof Input) {
				set.add(node);
			}
		}
		return set;
	}

	@Override
	public Set<Node> getFates() {
		Set<Node> set = new HashSet<>();
		for (Node node : getNodes()) {
			if (node instanceof FateNode) {
				set.add(node);
			}
		}
		return set;
	}

	@Override
	public void deactivateInputs() {
		getNodes().stream()
				.filter(node -> node instanceof Input)
				.forEach(node -> node.setActive(false));
	}

	@Override
	public boolean isNodeActive(String nodeTag) {
		return findNodeWithTag(nodeTag).isActive();
	}

	@Override
	public Fate update(){
		List<Fate> activatedFates = new ArrayList<>();
		boolean updates = ! nextUpdate.isEmpty(); //Check if map is empty to save time in case this is the first run.
			for (Node node : getNodes()) {
			if (updates && !(node instanceof Input)) {
				if(node instanceof Gene gene){
					gene.drugTaken(getInputs().stream().collect(Collectors.toMap(Node::getTag, Node::isActive)));
				}
				node.setActive(nextUpdate.get(node));  //update all the nodes with the map generated in the last update step. Inputs don't get updated by the network, only by external signals
			}
			if (node.isActive() && node instanceof FateNode) { //check in current status for activated fate nodes
				Fate computedFate = ((FateNode) node).getFate();
				activatedFates.add(computedFate);
				node.setActive(false); //deactivate fate after accounting for it
			}
			currentValues.put(node.getTag(), node.isActive()); //update the map with the current value of each node. needed even in the first run
		}

		//generate a map with all the projected values after the update. Each rule takes as parameter a map with the current state of every node, which was generated in the loop above.
		nextUpdate.putAll(getNodes().stream().filter(node -> !(node instanceof Input))
				.collect(Collectors.toMap(node -> node, node -> nodeState().apply(node, currentValues))));

		return selectFate(activatedFates);
	}

	protected Fate selectFate(List<Fate> activatedFates) {
		//fate rules
		if(activatedFates.size() >= 1) {
			Fate activeFate = null;
			if (activatedFates.size() == 1) { //it could be more than 1 in some cases, due to the random activation of genes at the beginning. In those cases the fate returned will depend on the decisionTimer.
				activeFate = activatedFates.get(0);
			} else {
				for (Fate value : Fate.values()) {
					if (activatedFates.contains(value)) {
						activeFate = value;
						break;
					}
				}
			}
			// necrosis, apoptosis and optionally growth arrest decisions are executed right away,
			// proliferation has to wait through the decision window
			boolean immediateArrest = SettingsProvider.SETTINGS_PROVIDER.getGeneralBoolean("instant-arrest");
			boolean executeFateNow = immediateArrest ? activeFate != Fate.PROLIFERATION :
					activeFate == Fate.APOPTOSIS || activeFate == Fate.NECROSIS || activeFate == Fate.ANERGY || activeFate == Fate.AICYTOKINES || activeFate == Fate.ACTINREM|| activeFate == Fate.PICYTOKINES|| activeFate == Fate.SURVIVAL;
			if (executeFateNow) {
				return activeFate;
			} else {
				if (!decisionTimerActive) {
					decisionTimerActive = true; //the decision timer only starts counting down from the first time a fate is activated.
				}
				lastActiveFate = activeFate;
				if (decisionTimer == 0) {
					resetDecisionTimer();
					decisionTimerActive = false;
					return lastActiveFate;
				}
			}
		}
		if(decisionTimerActive && decisionTimer > 0) decisionTimer--;
		return Fate.NO_FATE_REACHED;
	}

	@Override
	public void resetDecisionTimer(){
		decisionTimer = decisionWindow;
	}

	protected BiFunction<Node, Map<String, Boolean>, Boolean> nodeState(){
		return Node::computeState;
	}

	@Override
	public Node findNodeWithTag(String tag) {
		Node target = null;
		for (Node node : getGraph().vertexSet()) {
			if (node.getTag().equalsIgnoreCase(tag)) {
				target = node;
			}
		}
		return target;
	}

	/**
	 * Factory method for creating a new instance of Network (with the graphml importer constructor)
	 * which inputs and nodes are inactive but some of the genes are active at random
	 *
	 * @param filename the name of the graphml file, located in the resources folder.
	 * @param randomiseDecisionWindow should the decision window be a random number between 0 and the maximum, or should it be the maximum. Useful to make initial cells heterogeneous
	 * @param initial how nodes should be initialised
	 * @return a new instance of Network
	 */
	public static Network randomlyActivatedGraph(String filename, boolean randomiseDecisionWindow, String initial) {
		return new SynchronousBooleanNetwork(filename, randomiseDecisionWindow).turnNodes(false).activateGenes(initial);
	}

	@Override
	public Network activateGenes(String initial) {
		initialStateOption option;
		double prob = 0;
		try {
			option = initialStateOption.valueOf(initial.strip().toUpperCase());
		} catch(IllegalArgumentException iae){
			try{
				prob = Double.parseDouble(initial);
				option = initialStateOption.PROB;
				if(prob < 0 || prob > 1) throw new IllegalArgumentException("bad initial-states setting");
			} catch(NumberFormatException nfe){
				throw new IllegalArgumentException("bad initial-states setting");
			}
		}
		Random r = new Random();
		for (Node node : getGenes()) {
			switch(option){
				case ON -> node.setActive(true);
				case OFF -> node.setActive(false);
				case RANDOM -> node.setActive(r.nextBoolean());
				case PROB -> node.setActive(r.nextDouble() < prob);
			}
		}
		return this;
	}

	private enum initialStateOption{
		RANDOM,
		ON,
		OFF,
		PROB
	}

	@Override
	public Network turnGenes(boolean on){
		for (Node node : getGenes()) {
			node.setActive(on);
		}

		return this;
	}
	@Override
	public Network turnNodes(boolean on) {
		for (Node node : getNodes()) {
			node.setActive(on);
		}
		return this;
	}

	@Override
	public Network turnInputs(boolean on) {
		for (Node node : getInputs()) {
			node.setActive(on);
		}
		return this;
	}


	@Override
	public Network turnFates(boolean on) {
		for (Node node : getFates()) {
			node.setActive(on);
		}
		return this;
	}


	@Override
	public Network turnNode(String tag, boolean on) throws IllegalArgumentException{
		Node node = findNodeWithTag(tag);
		if(node == null){
			System.out.println("bad tag: " + tag);
			throw new IllegalArgumentException("No Node with that tag");
		}
		else {
			node.setActive(on);
			return this;
		}
	}


	@Override
	public void applyMutations(Map<String, Mutation> mutations) {
		for (String tag : mutations.keySet()) {
			Node node = Objects.requireNonNull(findNodeWithTag(tag), tag + " gene not found");
			Mutation mutation = mutations.get(tag);
			if (node instanceof Gene gene) {
				turnNode(tag, mutation.accountForMutation().orElse(node.isActive())); //if the mutation doesn't apply (probabilistic mutation) leave node with current state
				gene.applyMutation(mutation);
			} else throw new IllegalArgumentException(tag + " is not a gene");
		}
	}

	@Override
	public Map<String, Mutation> gatherMutations(){
		return getGenes().stream().collect(Collectors.toMap(Gene::getTag, Gene::getMutation));
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
					Mutation mutation = new Mutation(random.nextBoolean());
					gene.applyMutation(mutation);
				}
			}
		}
		return mutated;
	}

	protected static GraphImporter<Node, Edge> createImporter(VertexProvider<Node> vertexProvider){
		EdgeProvider<Node, Edge> edgeProvider = (from, to, label, attributes) -> {
			String sign = attributes.get("sign").getValue();
			if(sign.equals("positive") || sign.equals("negative")) return new Edge(to, from, sign.equals("positive"));
			else throw new IllegalArgumentException("Wrong 'sign' attribute for an edge, must be 'positive' or 'negative'");
		};

		GraphMLImporter<Node, Edge> importer =
				new GraphMLImporter<>(vertexProvider, edgeProvider);
		importer.setSchemaValidation(false); //todo check later as possible bug source
		return importer;
	}

	private static GraphImporter<Node, Edge> createImporter() {
		VertexProvider<Node> vertexProvider = (id, attributes) -> {
			String kind = attributes.get("kind").getValue();
			Node v;
			if(kind.equals("input")) v = new Input(id);
			else{
				String rule = attributes.get("rule").getValue();
				if(kind.equals("gene")) v = new Gene(id, rule);
				else if(kind.equals("fate")) v = new FateNode(id, rule);
				else throw new IllegalArgumentException("Wrong kind attribute for a node, must be 'gene', 'input' or 'fate'");
			}
			return v;
		};

		return createImporter(vertexProvider);
	}
	private static Graph<Node, Edge> loadGraphFile(String filename, Graph<Node, Edge> graph, GraphImporter<Node, Edge> importer) {
		File file = null;
		File graphmlFile = new File("C:/oncologyphd/microCJ-develop-tcells-cancer-id/microCJ-develop/core/src/main/resources/"+filename + ".graphml");
		if (graphmlFile.exists()) {
			file = graphmlFile;
		} else {
			Logger.warn("{} doesn't exist", graphmlFile);
			File zginmlFile = new File(filename + ".zginml");
			if (zginmlFile.exists()) { //try to find a zginml file and convert it
				try {
					GINMLConverter.run(zginmlFile.toString());
				} catch (IOException e) {
					e.printStackTrace();
				}
			} else Logger.warn("{} doesn't exist", zginmlFile);
		}
		if (file == null) { //load default
			var in = SynchronousBooleanNetwork.class.getResourceAsStream("/network.graphml");
			var reader = new BufferedReader(new InputStreamReader(in));
			try {
				importer.importGraph(graph, reader);
			} catch (ImportException e) {
				Logger.error("Error importing from network resource file");
				e.printStackTrace();
			}
		} else {
			try {
				importer.importGraph(graph, file);
			} catch (ImportException e) {
				Logger.error("Error importing from network external file");
				e.printStackTrace();
			}
		}
		return graph;
	}

	public static void setDecisionWindow(int window){
		decisionWindow = window;
	}
}