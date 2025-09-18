package graph;

import org.tinylog.Logger;

import java.util.Optional;
import java.util.Random;
import java.util.concurrent.ThreadLocalRandom;

public class Mutation {
	private Boolean sign;
	private int p;

	public Mutation(Boolean sign, Integer p) {
		this.sign = sign;
		this.p = p;
	}

	public Mutation(Boolean sign) {
		this.sign = sign;
		p = 1000;
	}

	/**
	 * Returns the mutation sign (positive or negative, true or false).
	 * If the mutation is run in a probabilistic setting, it will return an empty Optional with probability = 1000 - p
	 * @return An Optional containing a Boolean.
	 */
	public Optional<Boolean> accountForMutation(){
		if(sign == null) return Optional.empty();
		if(p == 1000) return Optional.of(sign);
		else{
			Random r = ThreadLocalRandom.current();
			Boolean result = null;
			if(r.nextInt(1000) < p) {
				result = sign;
			}
			return Optional.ofNullable(result);
		}
	}

	public void add(Mutation mutation){
		if(isEmpty()){ //adding to an empty mutation: just copy the added one
			sign = mutation.sign;
			p = mutation.p;
		} else if(! mutation.isEmpty()) { //if adding an empty mutation: do nothing
			int newP = p * signToNumber() + mutation.p * mutation.signToNumber();
			if (newP == 0) { //empty mutation
				sign = null;
				p = 0;
			} else {
				if (newP < 0) {
					sign = false;
					p = -newP;
				} else {
					sign = true;
					p = newP;
				}

				if (p > 1000) p = 1000;
			}
		}
	}

	public Integer getP() {
		return p;
	}

	String toStringSymbol(){
		if(isEmpty()) return "";
		else {
			if (sign) return "+";
			else return "-";
		}
	}

	@Override
	public String toString() {
		return toStringSymbol() + getProbString();
	}

	public int signToNumber(){
		if(isEmpty()) return 0;
		return sign ? 1 : -1;
	}

	public String getProbString(){
		if(p == 0) return "NA";
		else return String.valueOf(p);
	}

	public boolean isEmpty(){
		return sign == null;
	}

	public static Mutation from (GeneExpressionSet set, String tag) {
		return new Mutation(set.getSignForGene(tag), set.getProbabilityForGene(tag));
	}
}
