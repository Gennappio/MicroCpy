/*
Copyright 2019 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package graph;

import com.bpodgursky.jbool_expressions.Expression;
import com.bpodgursky.jbool_expressions.parsers.ExprParser;
import com.bpodgursky.jbool_expressions.rules.RuleSet;

import java.util.Map;

class Rule {
	private Expression<String> rule;
	private int p = 1000;

	private Rule(int p){
		this.p = p;
	}

	private Rule(Expression<String> rule) {
		this.rule = rule;
	}

	/**
	 * Return the result of the boolean rule using a map of nodes' tags and their values as input
	 * @param values A Map of tags and boolean activation values.
	 * @return the result of computing the boolean rule with the specified values.
	 */
	boolean computeRule(Map<String, Boolean> values) {
		Expression<String> resolved = RuleSet.assign(rule, values);

		return Boolean.parseBoolean(resolved.toString());
	}

	public int getP() {
		return p;
	}

	public void setP(int p) {
		this.p = p;
	}

	@Override
	public String toString() {
		return "Rule: " + rule.toString() + ", p: " + p;
	}

	static Rule parser(String stringRule) {
		//replace all operators with boolean symbols
		stringRule = stringRule.replace("and", "&")
				.replace("or", "|")
				.replace("not", "!");

		Expression<String> parsedExpression = RuleSet.simplify(ExprParser.parse(stringRule));

		return new Rule(parsedExpression);
	}

	static Rule parser(String stringRule, int p){
		if(p <= 0 || p > 1000)
			throw new IllegalArgumentException("Mutation p has to be a number between 1 and 1000 but is " + p);
		Rule rule = parser(stringRule);
		rule.p = p;
		return rule;
	}

	static Rule fixed(boolean result, int p){
		if(p <= 0 || p > 1000)
			throw new IllegalArgumentException("Mutation p has to be a number between 1 and 1000 but is " + p);
		return new Rule(p){
			@Override
			boolean computeRule(Map<String, Boolean> values) {
				return result;
			}

			@Override
			public String toString() {
				return "Rule: fixed " + result + ", p: " + p;
			}
		};
	}
}
