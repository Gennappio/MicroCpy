package graph;

import core.Fate;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;
import java.util.stream.Collectors;

public final class AsynchronousBooleanNetwork extends SynchronousBooleanNetwork{

	private AsynchronousBooleanNetwork(String filename, boolean randomiseDecisionWindow) {
		super(filename, randomiseDecisionWindow);
	}

	public static Network randomlyActivatedGraph(String filename, boolean randomiseDecisionWindow, String initial){
		return new AsynchronousBooleanNetwork(filename, randomiseDecisionWindow).turnNodes(false).activateGenes(initial);
	}

	@Override
	public Fate update() {
		List<Fate> activatedFates = new ArrayList<>();
		int p = ThreadLocalRandom.current().nextInt(getNodes().size());
		int i = 0;
		var it = getNodes().iterator();
		var currentState = getNodes().stream().collect(Collectors.toMap(Node::getTag, Node::isActive));
		while(it.hasNext()){
			Node node = it.next();
			if(i == p){
				node.setActive(node.computeState(currentState));
			}

			if (node.isActive() && node instanceof FateNode) {
				Fate computedFate = ((FateNode) node).getFate();
				activatedFates.add(computedFate);
				node.setActive(false); //deactivate fate after accounting for it
			}

			i++;
		}

		return selectFate(activatedFates);
	}
}
